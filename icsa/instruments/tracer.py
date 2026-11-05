"""In-sandbox tracer: ledger, provenance-carrying arrays, sinks, escapes (DESIGN.md).

Loaded at interpreter start through the sandbox hook (#7) by `install()`.
It must never change what agent code computes: every wrapper calls the
original function and returns its result; only the array subclass differs,
and it prints as `numpy.ndarray`. Internal errors fall back to "no lo,
collapsed hi" and are counted, never raised into agent code.

Dimensions in-process are file id `f`, time index `t`, lat index `j` and lon
index `i` in the file's own index space. `analyse` maps them to global units
offline, from the layout index, so the tracer does no I/O on the data path.
"""
from __future__ import annotations

import atexit
import builtins
import hashlib
import ctypes
import fcntl
import gc
import inspect
import io
import json
import os
import sys
import threading
import time
import traceback
import types
import warnings
import weakref
import zlib
from pathlib import Path

import numpy as np
import numpy.ma  # noqa: F401  (import before patching: numpy.ma calls np.array on import)

from . import prov as P

# numpy's own, as at import: the tracer's records must not go through the hooks on np.savez and np.load
_NP_SAVEZ_COMPRESSED, _NP_LOAD = np.savez_compressed, np.load

VAR = "analysed_sst"
_STATE: Tracer | None = None
_LIB_PREFIXES: tuple[str, ...] = ()
_OWN_DIR = str(Path(__file__).resolve().parent)
_KEEP_MODULES = ("xarray", "dask", "numpy", "icsa.instruments")
# Tracking through a run's own files (np.save, savez, load, pickle). Science's rule (#2): it stays only if K's finished cases keep median
# tool time within 1.5x and p90 within 3x of the same code without it. False takes it out in one line: such reads come back untracked,
# a pickle escapes as it did before, and those runs go to unknown.
OWN_FILES = False


# --------------------------------------------------------------- the tracer's own time
# Wall time spent inside the tracer's hooks, per process (science, #9 19:29Z): the outermost hook only (a hook
# inside a hook is not counted twice), less the time of the numpy or library call the hook wraps (`_native`). Two
# clock reads and a depth count per hook. Kept in memory and written, at most once a second and at exit, to
# `ttime.<pid>.json` in place (one fixed-size record), so a run that is killed or stopped at the cap leaves its
# count as of the last second. The depth is shared by the threads (the GIL orders the updates), so under threads
# the count is approximate.

_pc = time.perf_counter_ns
_TT = [0, 0, 0]          # ns inside hooks, hook calls, ns excluded so far (native calls inside hooks)
_TD = [0]                # hook depth
_TN = [0]                # native-call depth: only the outermost native interval is excluded
_TT_NEXT = [0]           # next time (perf_counter ns) the record is written
TT_EVERY_NS = 200_000_000


def _tt_enter():
    _TD[0] += 1
    return (_pc(), _TT[2]) if _TD[0] == 1 else None


def _tt_leave(t):
    _TD[0] -= 1
    if t is not None:
        now = _pc()
        _TT[0] += now - t[0] - (_TT[2] - t[1])
        _TT[1] += 1
        P._work(P.HOOK_WORK, P.HOOKS)
        if _STOPPED_NOTE[0] is not None and _TD[0] == 0:
            _note_stopped()
        if now >= _TT_NEXT[0]:
            _TT_NEXT[0] = now + TT_EVERY_NS
            st = _STATE
            if st is not None:
                st.tt_write()


def _native(fn, *a, **k):
    """A call a hook wraps (numpy's own operation, the library's read): its time is not the tracer's. A native
    call inside another (a hook run by numpy's own code) is part of the outer one, excluded once."""
    _TN[0] += 1
    t = _pc() if _TN[0] == 1 else None
    try:
        return fn(*a, **k)
    finally:
        _TN[0] -= 1
        if t is not None:
            _TT[2] += _pc() - t


def _timed(fn):
    def wrapped(*a, **k):
        t = _tt_enter()
        try:
            return fn(*a, **k)
        finally:
            _tt_leave(t)
    wrapped.__name__ = fn.__name__
    wrapped.__doc__ = fn.__doc__
    wrapped.__wrapped__ = fn
    return wrapped


def _after_fork_in_child():
    """A fork (os.fork, multiprocessing's default here) is a new process with a copy of the tracer: its own time
    count, its own locks (another thread may have held one at the fork) and its own streams (Tracer.after_fork)."""
    global _seq_lock, _SHARED_LOCK
    _TT[0] = _TT[1] = _TT[2] = 0
    _TD[0] = _TN[0] = 0
    _BUDGET_LEFT[0] -= P.budgeted()        # what the parent spent is in the parent's record
    P._PARTS[:] = [0, 0, 0]
    _SHARED_LOCK = threading.Lock()        # another thread may have held it at the fork
    _shared_open(_SHARED[2], child=True)   # its own lock: one shared with the parent would exclude nothing
    _TT_NEXT[0] = 0
    _seq_lock = threading.Lock()
    st = _STATE
    if st is not None:
        try:
            st.after_fork()
        except Exception as e:  # noqa: BLE001 - never into agent code
            st._fail(e)
    try:
        # What the run has spent, earlier workers included: a worker starts from the run's total, not its parent's view of it
        total = _shared_add()
        P._WORK[:] = [0, _next_look(total)]
        if _remaining(total) < 0 and not P.STOPPED[0]:
            _stop_tracking("work")
    except Exception:  # noqa: BLE001 - never into agent code
        pass


class _AfterFork:
    """multiprocessing's workers leave by os._exit, which skips atexit; their exit finalizers still run. A worker clears the
    finalizers when it starts and then runs the after-fork callbacks, so the finalizer is registered from one of those."""
    registered = False


_AFTER_FORK = _AfterFork()


def _register_worker_exit() -> None:
    mp_util = sys.modules.get("multiprocessing.util")
    if mp_util is None or _AfterFork.registered:
        return
    mp_util.register_after_fork(_AFTER_FORK, lambda _: mp_util.Finalize(None, _publish_at_exit, exitpriority=100))
    _AfterFork.registered = True


def _publish_at_exit() -> None:
    """A worker's last work, on the run's counter and in its time record, for the workers after it and for the offline sum."""
    try:
        _shared_add()
        if _STATE is not None:
            _STATE.tt_write()
    except Exception:  # noqa: BLE001 - never into agent code
        pass


def _before_fork() -> None:
    try:
        _register_worker_exit()
        _shared_add()                       # the parent's work so far is on the run's counter, once, before the child copies it
    except Exception:  # noqa: BLE001 - never into agent code
        pass


os.register_at_fork(before=_before_fork, after_in_child=_after_fork_in_child)


# --------------------------------------------------------------- the array

def _plain(x):
    """The same buffer as a plain ndarray (internal use; never recorded)."""
    return np.ndarray.view(x, np.ndarray)


# numpy's own attribute descriptors, for the attributes TArray intercepts on assignment
_ND_SHAPE = np.ndarray.__dict__["shape"]
_ND_DTYPE = np.ndarray.__dict__["dtype"]
_ND_STRIDES = np.ndarray.__dict__["strides"]
_ND_REAL = np.ndarray.__dict__["real"]
_ND_IMAG = np.ndarray.__dict__["imag"]
_ND_FLAT = np.ndarray.__dict__["flat"]
_ND_BASE = np.ndarray.__dict__["base"]


def _set_as_numpy(descriptor, x, value) -> None:
    """numpy warns of a deprecated setter for its own type only: it is asked on a plain view, so the agent has the same warning at
    the same line."""
    with warnings.catch_warnings(record=True) as said:
        warnings.simplefilter("always")
        descriptor.__set__(np.ndarray.view(x, np.ndarray), value)
    descriptor.__set__(x, value)
    for w in said:
        warnings.warn(w.message, w.category, skip_file_prefixes=(_OWN_DIR,))


def _refuse_resize() -> None:
    """numpy's own refusal, in its own words."""
    a = np.ndarray((1,))
    b, c = a, a  # noqa: F841
    a.resize(2)


def _take_ownership(x) -> None:
    """numpy's own way to replace an array's data in place, in pickle's format: x owns the copy and has no base after it."""
    plain = np.ndarray.view(x, np.ndarray)
    fortran = bool(plain.flags.f_contiguous and not plain.flags.c_contiguous)
    raw = plain.tolist() if plain.dtype.hasobject else plain.tobytes(order="F" if fortran else "C")
    np.ndarray.__setstate__(x, (1, plain.shape, plain.dtype, fortran, raw))


class TArray(np.ndarray):
    """An ndarray carrying provenance. Prints and names itself as ndarray."""

    _p: P.Prov = P.Prov.none()

    def __dir__(self):
        return dir(np.ndarray)

    def __setattr__(self, name, value):
        # ndarray has no instance dict: x.foo = 1 raises there, in these words
        if name != "_p" and not hasattr(TArray, name):
            raise AttributeError(f"'numpy.ndarray' object has no attribute '{name}'")
        object.__setattr__(self, name, value)

    def __array_finalize__(self, obj):
        P._work(P.HOOK_WORK, P.HOOKS)
        # Arrays made by methods we do not model: lo nothing, hi collapsed.
        # Modelled paths overwrite `_p` right after.
        p = getattr(obj, "_p", None)
        if p is None or p.is_empty():
            self._p = P.Prov.none()
        elif _same_elements(obj, self):
            self._p = p          # a view of exactly the same elements (e.g. a masked array's data)
        else:
            self._p = P.hi_only(p, self.ndim)
        _register(self)

    # ---- printing: identical to ndarray, recorded as an observation
    def __repr__(self):
        _observe(self)
        return np.ndarray.__repr__(_plain(self))

    def __str__(self):
        _observe(self)
        return np.ndarray.__str__(_plain(self))

    def __format__(self, spec):
        _observe(self)
        return np.ndarray.__format__(_plain(self), spec)

    # ---- escapes to plain Python
    def tolist(self):
        _escape(self, "tolist")
        return _plain(self).tolist()

    def item(self, *a):
        _escape(self, "item")
        return _plain(self).item(*a)

    def tobytes(self, *a, **k):
        _escape(self, "tobytes")
        return _plain(self).tobytes(*a, **k)

    def tofile(self, *a, **k):
        _escape(self, "tofile")
        return _plain(self).tofile(*a, **k)

    def __float__(self):
        _escape(self, "float")
        return float(_plain(self))

    def __int__(self):
        _escape(self, "int")
        return int(_plain(self))

    def __index__(self):
        _escape(self, "index")
        return _plain(self).__index__()

    def __bool__(self):
        _escape(self, "bool")
        return bool(_plain(self))

    def __complex__(self):
        _escape(self, "complex")
        return complex(_plain(self))

    def __reduce_ex__(self, protocol):
        travel = _prov_for_pickle(self._p) if not self._p.is_empty() else None
        if travel is None:
            _escape(self, "pickle")
            return _plain(self).__reduce_ex__(protocol)
        return _rebuild_tracked, (_plain(self), *travel)

    def __array__(self, *a, **k):
        # A plain view of this buffer, as view(np.ndarray): the values leave tracking and no alias keeps its lo.
        _escape(self, "plain_view")
        _invalidate(self, None, include_self=True)
        return np.ndarray.__array__(_plain(self), *a, **k)

    def __iter__(self):
        if self.ndim <= 1:
            _escape(self, "iter")
            return iter(_plain(self))
        return (self[k] for k in range(len(self)))

    @property
    def flat(self):
        # Writes through a flatiter cannot be observed: lo of this buffer is no longer trusted.
        _escape(self, "flat")
        _invalidate(self, None, include_self=True)
        return _plain(self).flat

    @flat.setter
    def flat(self, value):
        _ND_FLAT.__set__(_plain(self), _unwrap(value))
        self._mutated_unmodelled(value)

    # ---- in-place attribute writes (Codex on bf0cdec): numpy changes the array itself, so
    # the provenance follows, or the lower bound is dropped. Getters are numpy's own.
    @property
    def shape(self):
        return _ND_SHAPE.__get__(self)

    @shape.setter
    def shape(self, value):
        # numpy assigns a shape only where no copy is needed, always in C index order (it
        # raises otherwise): the elements move exactly as in reshape(order="C").
        old_shape, old_p = _ND_SHAPE.__get__(self), self._p
        _set_as_numpy(_ND_SHAPE, self, value)
        new_shape = _ND_SHAPE.__get__(self)
        self._p = _try(lambda: P.reshape(old_p, old_shape, new_shape), old_p, len(new_shape))

    @property
    def dtype(self):
        return _ND_DTYPE.__get__(self)

    @dtype.setter
    def dtype(self, value):
        # The same item size keeps every element in its position (its bits reinterpreted);
        # another one changes the last axis, where new elements straddle old ones: unmodelled.
        old_shape, old_p = _ND_SHAPE.__get__(self), self._p
        _ND_DTYPE.__set__(self, value)
        if _ND_SHAPE.__get__(self) != old_shape:
            self._p = P.hi_only(old_p, self.ndim)

    @property
    def strides(self):
        return _ND_STRIDES.__get__(self)

    @strides.setter
    def strides(self, value):
        _ND_STRIDES.__set__(self, value)
        _remapped(self, "strides_set")

    @property
    def real(self):
        return _ND_REAL.__get__(self)

    @real.setter
    def real(self, value):
        _ND_REAL.__set__(_plain(self), _unwrap(value))
        if np.iscomplexobj(_plain(self)):
            self._mutated_unmodelled(value)
        else:                         # the real part of a real array is the array itself
            _guard_set(self, Ellipsis, value)
            _invalidate(self, _prov(value))

    @property
    def imag(self):
        return _ND_IMAG.__get__(self)

    @imag.setter
    def imag(self, value):
        _ND_IMAG.__set__(_plain(self), _unwrap(value))     # a real array raises, as in numpy
        self._mutated_unmodelled(value)

    @property
    def data(self):
        # The raw buffer (a writable memoryview): writes through it bypass every model,
        # so no alias of this buffer keeps its lo; the values also leave tracking.
        # (The writing library never sees a tracked sink value: hooks hand it plain arrays.)
        _raw_buffer(self, "data_buffer")
        return _plain(self).data

    # ---- indexing
    def __getitem__(self, key):
        t = _tt_enter()
        try:
            r = _native(np.ndarray.__getitem__, _plain(self), _unwrap(key))
            return _guard(lambda: _index_result(self, key, r), r, self, key)
        finally:
            _tt_leave(t)

    def __setitem__(self, key, value):
        t = _tt_enter()
        try:
            _native(np.ndarray.__setitem__, _plain(self), _unwrap(key), _unwrap(value))
            _guard_set(self, key, value)
            _invalidate(self, _prov(value))
            _constant_write(self, key, value)
        finally:
            _tt_leave(t)

    # ---- methods that change the element mapping: numpy's own method first
    def reshape(self, *shape, order="C", copy=None):
        r = np.ndarray.reshape(_plain(self), *shape, order=order, copy=copy)
        return _wrap(r, _order_prov(self, r, order))

    def transpose(self, *axes):
        r = np.ndarray.transpose(_plain(self), *axes)
        perm = axes[0] if len(axes) == 1 and isinstance(axes[0], (tuple, list)) else axes
        if not perm or perm == (None,):
            perm = tuple(range(self.ndim))[::-1]
        else:
            perm = tuple(int(a) % self.ndim for a in perm)
        return _wrap(r, _try(lambda: P.transpose(self._p, perm), self._p, r.ndim))

    @property
    def T(self):
        return self.transpose()

    def swapaxes(self, a, b, /):
        r = np.ndarray.swapaxes(_plain(self), a, b)
        perm = list(range(self.ndim))
        a, b = a % self.ndim, b % self.ndim
        perm[a], perm[b] = perm[b], perm[a]
        return _wrap(r, _try(lambda: P.transpose(self._p, perm), self._p, r.ndim))

    def ravel(self, order="C"):
        r = np.ndarray.ravel(_plain(self), order)
        return _wrap(r, _order_prov(self, r, order))

    def flatten(self, order="C"):
        r = np.ndarray.flatten(_plain(self), order)
        return _wrap(r, _order_prov(self, r, order))

    def squeeze(self, axis=None):
        r = np.ndarray.squeeze(_plain(self), axis)
        return _wrap(r, _try(lambda: P.reshape(self._p, self.shape, r.shape), self._p, r.ndim))

    def copy(self, order="C"):
        return _wrap(np.ndarray.copy(_plain(self), order), self._p)

    # ---- methods whose result numpy builds as a base-class array or a plain scalar, with no hook: a selection made from
    # tracked values, as np.nonzero and np.argmax are modelled
    def nonzero(self):
        r = np.ndarray.nonzero(_plain(self))
        q = _guard(lambda: _nonzero_result(self, r), None, self) if self.ndim else None
        if q is None or q is _NOT:
            _escape(self, "nonzero")
            return r
        return q

    def take(self, indices, axis=None, out=None, mode="raise"):
        r = np.ndarray.take(_plain(self), _unwrap(indices), axis, _unwrap(out), mode)
        ip = _prov(indices)
        nd = np.ndim(r)
        p = P.hi_only(P.union([self._p] + ([ip] if ip is not None else []), nd), nd)
        if out is not None:
            _finish_one(r, p, out, True)
            return out
        return _wrap(r, p) if isinstance(r, np.ndarray) else _scalar(r, p)

    def astype(self, dtype, *a, **k):
        r = np.ndarray.astype(_plain(self), dtype, *a, **k)
        return _wrap(r, self._p) if r.shape == self.shape else _wrap(r, P.hi_only(self._p, r.ndim))

    def view(self, *a, **k):
        if not a and not k:
            r = np.ndarray.view(self)
            r._p = self._p
            return r
        # ndarray.view([dtype][, type]), either positional or by keyword
        dtype, typ = k.get("dtype"), k.get("type")
        rest = list(a)
        if rest and isinstance(rest[0], type) and issubclass(rest[0], np.ndarray) and typ is None:
            typ = rest.pop(0)
        elif rest:
            dtype = rest.pop(0)
            if rest:
                typ = rest.pop(0)
        if typ is np.ma.MaskedArray and dtype is None:
            # A masked view is tracked (its provenance is kept current, hooks.py):
            # numpy's masked-array slicing and construction take this path.
            return np.ndarray.view(self, typ)
        if typ is not None and typ is not TArray:
            # A view of another class (plain ndarray, recarray, matrix ...): writes through
            # it are invisible, so provenance leaves tracking and no alias keeps its lo.
            _escape(self, "plain_view")
            _invalidate(self, None, include_self=True)
            return np.ndarray.view(self, *a, **k)
        r = np.ndarray.view(_plain(self), dtype) if dtype is not None else np.ndarray.view(_plain(self))
        if type(r) is not np.ndarray:          # a dtype with its own array type (np.record)
            _escape(self, "plain_view")
            _invalidate(self, None, include_self=True)
            return r
        p = self._p if r.shape == self.shape else P.hi_only(self._p, r.ndim)
        return _wrap(r, p)

    # ---- in-place mutations
    def fill(self, value, /):
        np.ndarray.fill(_plain(self), _unwrap(value))
        vp = _prov(value)
        self._p = P.Prov.none() if vp is None else P.hi_only(vp, self.ndim)
        _invalidate(self, vp)
        _constant_write(self, Ellipsis, value)

    def sort(self, axis=-1, kind=None, order=None, **k):
        np.ndarray.sort(_plain(self), axis=axis, kind=kind, order=order, **k)
        self._p = _try(lambda: P.mix_axis(self._p, self.shape, axis), self._p, self.ndim)
        _invalidate(self, self._p)

    def _mutated_unmodelled(self, values=None):
        vp = _prov(values)
        parts = [self._p] + ([vp] if vp is not None else [])
        self._p = P.hi_only(P.union(parts, self.ndim), self.ndim)
        _invalidate(self, vp)

    def put(self, indices, values, /, mode="raise"):
        try:
            np.ndarray.put(_plain(self), _unwrap(indices), _unwrap(values), mode)
        finally:
            self._mutated_unmodelled(values)

    def partition(self, *a, **k):
        np.ndarray.partition(_plain(self), *a, **k)
        # The elements move along the axis: a view taken before now holds values from all of them.
        self._mutated_unmodelled(self)

    def resize(self, *a, refcheck=True, **k):
        # A tracked array is a view of the array numpy made, so numpy would refuse it as not owning its data, and the tracer's own
        # weak references and this call's frame would count as others holding it. An agent's array that no one else holds owns its
        # data, for the agent: make that true, leave the tracer's records out of it, then numpy's own resize. A view of something
        # still in use gets numpy's answer. The counts: the agent's name for it, this call's self, getrefcount's argument.
        base = _ND_BASE.__get__(self)
        owned = base is None and self.flags.owndata
        alone = type(base) is np.ndarray and base.flags.owndata and sys.getrefcount(base) <= 3
        if owned or alone:
            if refcheck and sys.getrefcount(self) > 3:
                _refuse_resize()
            _unregister(base if alone else self, self)
            del base
            if alone:
                _take_ownership(self)
            refcheck = False
        else:
            del base
        try:
            np.ndarray.resize(self, *a, refcheck=refcheck, **k)
        finally:
            if owned or alone:
                _register(self)
        self._mutated_unmodelled()

    def setfield(self, val, *a, **k):
        np.ndarray.setfield(_plain(self), _unwrap(val), *a, **k)
        self._mutated_unmodelled(val)

    def byteswap(self, inplace=False):
        r = np.ndarray.byteswap(_plain(self), inplace)
        if inplace:
            self._mutated_unmodelled()
            return self
        return _wrap(r, P.hi_only(self._p, r.ndim))

    # ---- numpy protocols
    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        return _ufunc(ufunc, method, inputs, kwargs)

    def __array_function__(self, func, types, args, kwargs):
        return _function(func, args, kwargs)


TArray.__name__ = "ndarray"
TArray.__qualname__ = "ndarray"
TArray.__module__ = "numpy"


def _reducing_method(name):
    """`x.mean()` and the like: numpy rebuilds a scalar result from its dtype (`ret.dtype.type(...)`),
    which would drop the provenance its ufuncs kept. An array result keeps it through them."""
    method = getattr(np.ndarray, name)

    def reduced(self, *a, **k):
        axis = a[0] if a else k.get("axis")
        if len(a) <= 1 and not (set(k) - {"axis"}) and (axis is None or self.ndim <= 1):
            r = method(_plain(self), *a, **k)
            if not isinstance(r, np.ndarray):
                return _ret(r, _try(lambda: P.reduce(self._p, self.shape, axis), P.hi_only(self._p, 0), 0))
            return _wrap(r, _try(lambda: P.reduce(self._p, self.shape, axis), P.hi_only(self._p, r.ndim), r.ndim))
        return method(self, *a, **k)
    reduced.__name__ = name
    reduced.__doc__ = method.__doc__
    return reduced


for _name in ("mean", "std", "var", "sum", "prod", "min", "max", "argmax", "argmin"):
    setattr(TArray, _name, _reducing_method(_name))
del _name


# --------------------------------------------------------------- scalars
# A value reduced from tracked data depends on those units. numpy gives it back as a scalar, which would
# drop that: a Python loop's `thr[d, c] = np.nanpercentile(pool, 90)` would then write a constant. So a
# floating scalar reduced from tracked data is a subclass carrying the reduced array's provenance: arithmetic
# propagates it and the setitem hook reads it. `float()`, `int()`, `.item()`, `.tolist()` and anything else
# outside numpy strip it, the safe direction, and the units stay on record as an escape from the moment the
# scalar exists, so what leaves through `math.sqrt(v)` cannot go missing from the upper bound.
# Same type name and repr as numpy's; `isinstance`, `format`, `json.dumps`, hashing and dict keys as for a plain
# scalar (tests/instruments/test_scalars.py).

_ARRAYLIKE = (np.ndarray, list, tuple)
_SCALARLIKE = (int, float, complex, np.number, np.bool_)


def _scalar_op_result(r, self, other, comparison: bool):
    """A scalar operator's result (computed by numpy's own scalar code, so the values are numpy's) with the
    provenance of its tracked operands."""
    p = self._p
    op = getattr(other, "_p", None) if isinstance(other, _TSCALARS) else None
    if op is not None and not op.is_empty():
        p = P.union([p, op], 0)
        if comparison:
            p = P.Prov(p.lo, p.hi, p.flags | {DATA_COMPARISON})
    if isinstance(r, tuple):
        return tuple(_scalar(x, p) for x in r)
    return _scalar(r, p)


def _make_tscalar(base):
    def binary(name, ufunc, reflected=False, comparison=False):
        base_op = getattr(base, name)

        def op(self, other):
            if isinstance(other, _ARRAYLIKE):
                # numpy hands an array operand to the ufunc; so does this, element by element
                return ufunc(other, self) if reflected else ufunc(self, other)
            if isinstance(other, _SCALARLIKE):
                r = base_op(base(self), _unwrap(other))
                return r if r is NotImplemented else _scalar_op_result(r, self, other, comparison)
            return base_op(base(self), other)
        op.__name__ = name
        return op

    def unary(name):
        base_op = getattr(base, name)

        def op(self):
            return _scalar(base_op(base(self)), self._p)
        op.__name__ = name
        return op

    def __new__(cls, value, p):
        s = base.__new__(cls, value)
        s._p = p
        return s

    def __pow__(self, other, mod=None):
        if mod is None and isinstance(other, _ARRAYLIKE):
            return np.power(self, other)
        if mod is None and isinstance(other, _SCALARLIKE):
            r = base.__pow__(base(self), _unwrap(other))
            return r if r is NotImplemented else _scalar_op_result(r, self, other, False)
        return base.__pow__(base(self), _unwrap(other), mod)

    def __round__(self, ndigits=None):
        r = base.__round__(base(self), ndigits)
        return r if ndigits is None or not isinstance(r, base) else type(self)(r, self._p)

    ns = {"__new__": __new__, "__slots__": ("_p",), "__hash__": base.__hash__, "__pow__": __pow__,
          "__round__": __round__,
          "__array_ufunc__": lambda self, ufunc, method, *inputs, **kwargs: _ufunc(ufunc, method, inputs, kwargs),
          "__array_function__": lambda self, func, types, args, kwargs: _function(func, args, kwargs),
          "__reduce_ex__": lambda self, protocol: base(self).__reduce_ex__(protocol),
          "__copy__": lambda self: base(self), "__deepcopy__": lambda self, memo: base(self),
          "__neg__": unary("__neg__"), "__pos__": unary("__pos__"), "__abs__": unary("__abs__"),
          "__rpow__": binary("__rpow__", np.power, True)}
    for name, ufunc in (("add", np.add), ("sub", np.subtract), ("mul", np.multiply), ("truediv", np.true_divide),
                        ("floordiv", np.floor_divide), ("mod", np.remainder), ("divmod", np.divmod)):
        ns[f"__{name}__"] = binary(f"__{name}__", ufunc)
        ns[f"__r{name}__"] = binary(f"__r{name}__", ufunc, True)
    for name, ufunc in (("lt", np.less), ("le", np.less_equal), ("gt", np.greater), ("ge", np.greater_equal),
                        ("eq", np.equal), ("ne", np.not_equal)):
        ns[f"__{name}__"] = binary(f"__{name}__", ufunc, comparison=True)
    t = type(base.__name__, (base,), ns)
    t.__qualname__ = base.__qualname__
    t.__module__ = base.__module__
    return t


TFloat64 = _make_tscalar(np.float64)
TFloat32 = _make_tscalar(np.float32)
_TSCALARS = (TFloat64, TFloat32)
_SCALAR_OF = {np.float64: TFloat64, np.float32: TFloat32}
_BASE_OF = {TFloat64: np.float64, TFloat32: np.float32}


def _scalar(r, p: P.Prov):
    """A scalar result computed from tracked inputs: it escapes (the units stay on record), and carries the
    provenance if it is a floating scalar."""
    if p is None or p.is_empty():
        return r
    _escape_prov(p, "scalar", dt=getattr(getattr(r, "dtype", None), "char", None), value=r)
    t = _SCALAR_OF.get(type(r))
    return r if t is None else t(r, p)


def _order_prov(x: TArray, r, order) -> P.Prov:
    """Provenance of a reshape/ravel in `order`: modelled for C traversal only."""
    c_like = order == "C" or (order in ("A", "K") and _plain(x).flags.c_contiguous)
    if not c_like:
        return P.hi_only(x._p, r.ndim)
    return _try(lambda: P.reshape(x._p, x.shape, r.shape), x._p, r.ndim)


# Every live TArray, grouped by the object that owns its buffer, so that a write
# through one view can invalidate the lower bounds of the others.
_ALIASES: dict[int, dict[int, weakref.ref]] = {}
_ALIAS_ENDS: dict[int, weakref.finalize] = {}


def _owner(a):
    b = a
    while isinstance(getattr(b, "base", None), np.ndarray):
        b = b.base
    return b.base if getattr(b, "base", None) is not None else b


def _register(a):
    try:
        o = _owner(a)
        refs = _ALIASES.get(id(o))
        if refs is None:
            refs = _ALIASES[id(o)] = {}
            try:
                _ALIAS_ENDS[id(o)] = weakref.finalize(o, _alias_end, id(o))
            except TypeError:
                pass
        refs[id(a)] = weakref.ref(a, lambda _r, k=id(a), d=refs: d.pop(k, None))
    except Exception:  # noqa: BLE001
        pass


def _alias_end(k) -> None:
    _ALIASES.pop(k, None)
    _ALIAS_ENDS.pop(k, None)


def _unregister(owner, a) -> None:
    """numpy refuses to resize an array with a weak reference to it: the tracer's own go, and _register puts them back."""
    refs = _ALIASES.get(id(owner))
    if refs is not None:
        refs.pop(id(a), None)
    if owner is a and not refs:
        end = _ALIAS_ENDS.pop(id(a), None)
        if end is not None:
            end.detach()
        _ALIASES.pop(id(a), None)


# Owners of buffers whose raw bytes were handed out while they held no provenance.
# A tracked write into one later is unsafe (the old memoryview can overwrite it).
_EXPOSED: set[int] = set()


def _buffer_tracked(x) -> bool:
    """x, or a live alias sharing its memory, carries provenance."""
    if isinstance(x, TArray) and not x._p.is_empty():
        return True
    for r in list((_ALIASES.get(id(_owner(x))) or {}).values()):
        z = r()
        if isinstance(z, TArray) and not z._p.is_empty() and np.may_share_memory(_plain(z), _plain(x)
                                                                                 if isinstance(x, TArray) else x):
            return True
    return False


def _raw_buffer(x, kind):
    """x's raw buffer was handed out (ndarray.data, frombuffer over it)."""
    try:
        if _buffer_tracked(x):
            if isinstance(x, TArray):
                _escape(x, kind)
            _invalidate(x, None, include_self=True)
            _count("raw_buffer")
        else:
            o = _owner(x)
            if id(o) not in _EXPOSED:
                _EXPOSED.add(id(o))
                try:
                    # forget the owner when it dies (a live memoryview keeps it alive),
                    # so a later array reusing its id is not taken as exposed
                    weakref.finalize(o, _EXPOSED.discard, id(o))
                except TypeError:
                    pass                    # not weak-referenceable: kept (conservative)
    except Exception:  # noqa: BLE001
        _count("internal_error")
        _count("raw_buffer")


def _remapped(x, kind):
    """x's elements were remapped in place in a way no model follows: new strides can
    reach elements of the buffer outside x's provenance. If the buffer carries provenance,
    the values escape with what was known of them, no alias keeps its lo, the run is never
    complete (raw_buffer) and the upper bound falls back to the loaded extent
    (view_remapped). An untracked buffer has nothing to lose."""
    try:
        p = _ma_prov(x) if isinstance(x, np.ma.MaskedArray) else _prov(x)
        if not ((p is not None and not p.is_empty()) or _buffer_tracked(x)):
            return
        if p is not None and not p.is_empty():
            _escape_prov(p, kind)
        _invalidate(x, None, include_self=True)
        _count("raw_buffer")
        _count("view_remapped")
    except Exception:  # noqa: BLE001
        _count("internal_error")
        _count("raw_buffer")
        _count("view_remapped")


def _invalidate(y, extra: P.Prov | None, include_self=False):
    """y's buffer was written: other live views of it hold stale provenance.
    Their lo is dropped and their hi widened by what was written."""
    if _EXPOSED and extra is not None and not extra.is_empty():
        try:
            if id(_owner(y)) in _EXPOSED:
                _count("raw_buffer")         # tracked values into an exposed buffer
        except Exception:  # noqa: BLE001
            _count("raw_buffer")
    try:
        refs = _ALIASES.get(id(_owner(y)))
        if not refs:
            return
        for r in list(refs.values()):
            z = r()
            if z is None or (z is y and not include_self):
                continue
            if isinstance(z, np.ma.MaskedArray):
                _invalidate_masked(z, y, extra, include_self)
                continue
            if not isinstance(z, TArray):
                continue
            if z is not y and not np.may_share_memory(_plain(z), _plain(y)):
                continue
            if z is not y and not z._p.lo and (extra is None or extra.is_empty()):
                continue                   # nothing to drop and nothing tracked to add
            parts = [z._p] + ([extra] if extra is not None and not extra.is_empty() else [])
            z._p = P.hi_only(P.union(parts, z.ndim), z.ndim)
            _count("alias_invalidated")
    except Exception:  # noqa: BLE001
        _count("internal_error")


def _same_elements(a, b) -> bool:
    try:
        return (isinstance(a, np.ndarray) and a.shape == b.shape and a.strides == b.strides
                and a.dtype.itemsize == b.dtype.itemsize
                and a.__array_interface__["data"][0] == b.__array_interface__["data"][0])
    except Exception:  # noqa: BLE001
        return False


def _wrap(r, p: P.Prov):
    if isinstance(r, np.ma.MaskedArray):
        _set_ma_prov(r, p)
        return r
    if isinstance(r, np.ndarray):
        if type(r) is not TArray:
            r = np.ndarray.view(r, TArray)
        r._p = p
        return r
    return r


# ---- masked arrays
# A MaskedArray's provenance is its own attribute `_p` (numpy copies attributes of the
# array it was viewed from into the masked array's dict). It is authoritative: hooks keep
# it current on every write (_invalidate, _update_from and the in-place methods patched in
# hooks.py), and its data views (`_baseclass` TArray) take it from there.

def _ma_prov(x) -> P.Prov | None:
    if P.STOPPED[0]:
        return None
    try:
        p = x.__dict__.get("_p")
    except AttributeError:
        return None
    return p if type(p) is P.Prov else None


def _set_ma_prov(m, p: P.Prov | None):
    try:
        d = m.__dict__
        if p is None or P.STOPPED[0]:
            d.pop("_p", None)
            return
        d["_p"] = p
        if d.get("_baseclass", np.ndarray) is np.ndarray:
            d["_baseclass"] = TArray            # data views carry the provenance
        _register(m)
    except Exception:  # noqa: BLE001
        _count("internal_error")


def _invalidate_masked(z, y, extra, include_self):
    """A write into y's buffer: a masked array z over the same buffer is stale. If z has
    exactly y's elements and y's provenance was just set by the write, z takes it;
    otherwise z's lower bound is dropped and its upper bound widened."""
    zp = _ma_prov(z)
    if zp is None:
        return
    zplain = np.ndarray.view(z, np.ndarray)
    yplain = np.ndarray.view(y, np.ndarray)
    if z is not y and not np.may_share_memory(zplain, yplain):
        return
    if (not include_self and z is not y and isinstance(y, TArray)
            and _same_elements(zplain, yplain)):
        z.__dict__["_p"] = y._p
        return
    parts = [zp] + ([extra] if extra is not None and not extra.is_empty() else [])
    z.__dict__["_p"] = P.hi_only(P.union(parts, z.ndim), z.ndim)
    _count("alias_invalidated")


def _prov(x):
    p = getattr(x, "_p", None) if isinstance(x, (TArray, *_TSCALARS)) else None
    if p is None and isinstance(x, np.ma.MaskedArray):
        p = _ma_prov(x)
        if p is None:
            d = x._data
            p = getattr(d, "_p", None) if isinstance(d, TArray) else None
    return p


def _unwrap(x):
    if isinstance(x, TArray):
        return _plain(x)
    if isinstance(x, _TSCALARS):
        return _BASE_OF[type(x)](x)
    if isinstance(x, tuple):
        return tuple(_unwrap(v) for v in x)
    if isinstance(x, list):
        return [_unwrap(v) for v in x]
    if isinstance(x, dict):
        return {k: _unwrap(v) for k, v in x.items()}
    return x


def _collect(x, out: list):
    """All tracked arrays and scalars inside x (args, lists, tuples, dicts, masked arrays)."""
    if isinstance(x, (TArray, *_TSCALARS)):
        if not x._p.is_empty():
            out.append(x)
    elif isinstance(x, np.ma.MaskedArray):
        mp = _ma_prov(x)
        if mp is not None and not mp.is_empty():
            v = np.ndarray.view(x, TArray)       # its data, with the masked array's provenance
            v._p = mp
            out.append(v)
        else:
            d = x._data
            if isinstance(d, TArray) and not d._p.is_empty():
                out.append(d)
        m = x.__dict__.get("_mask") if hasattr(x, "__dict__") else None
        if isinstance(m, TArray) and not m._p.is_empty():
            out.append(m)
    elif isinstance(x, (tuple, list)):
        for v in x:
            _collect(v, out)
    elif isinstance(x, dict):
        for v in x.values():
            _collect(v, out)
    return out


def _try(fn, fallback: P.Prov, ndim: int) -> P.Prov:
    try:
        return fn()
    except Exception:  # noqa: BLE001 - tracer errors never reach agent code
        _count("internal_error")
        return P.hi_only(fallback, ndim)


def _guard(fn, r, src, key=None):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        _count("internal_error")
        tracked = _collect(key, []) if key is not None else []
        if isinstance(r, np.ndarray):
            return _wrap(r, P.hi_only(P.union([src._p, *(t._p for t in tracked)], r.ndim), r.ndim))
        return r


def _index_result(x: TArray, key, r):
    if not isinstance(r, np.ndarray):
        if not x._p.is_empty():
            _escape(x, "scalar_index")
        return r
    if x._p.is_empty() and not _collect(key, []):
        return _wrap(r, P.Prov.none())
    plain_key = _unwrap(key)
    p, shape = P.getitem(x._p, x.shape, plain_key)
    if shape != r.shape:
        _count("shape_mismatch")
        return _wrap(r, P.hi_only(x._p, r.ndim))
    kp = _key_prov(key, x.shape, plain_key, r.ndim)
    if kp is not None:
        p = P.union([p, kp], r.ndim)
    return _wrap(r, p)


def _key_prov(key, shape, plain_key, out_ndim):
    """Selection dependence: a tracked index or mask lends its provenance."""
    tracked = _collect(key, [])
    if not tracked:
        return None
    rk = P.resolve_key(plain_key, shape)
    adv = [k for k, a in enumerate(rk.out_axes) if a[0] == "adv"]
    parts = []
    for t in tracked:
        tv = _plain(t)
        if t.dtype == bool and adv:
            q, _ = P.getitem(t._p, t.shape, (tv,))
            parts.append(P.key_dependence(q, q, None, [adv[0]], out_ndim))
        elif adv and t.ndim == 1:
            parts.append(P.key_dependence(t._p, t.shape, None, [adv[0]], out_ndim))
        else:
            parts.append(P.Prov((), (P.collapse(t._p.hi, out_ndim),)))
    return P.union(parts, out_ndim)


def _guard_set(x: TArray, key, value):
    try:
        vp = _prov(value)
        vshape = np.shape(value)
        plain_key = _unwrap(key)
        kp = None
        tracked_key = _collect(key, [])
        if tracked_key:
            parts = []
            for t in tracked_key:
                if t.dtype == bool and t.shape == x.shape:
                    parts.append(t._p)
                else:
                    parts.append(P.Prov((), (P.collapse(t._p.hi, x.ndim),)))
            kp = P.union(parts, x.ndim)
        x._p = P.setitem(x._p, x.shape, plain_key, vp, vshape, kp)
    except Exception:  # noqa: BLE001
        _count("internal_error")
        vp = _prov(value)
        parts = [x._p] + ([vp] if vp is not None else []) + [t._p for t in _collect(key, [])]
        x._p = P.hi_only(P.union(parts, x.ndim), x.ndim)


# --------------------------------------------------------------- ufuncs

# Tracked values written into an exact ndarray (`plain[...] = tracked`) leave no trace: the write is numpy's, in C, with no
# hook, so that array holds data no provenance names. Such an array can reach a result in one of two ways: alone, and the
# sink is uncovered; or by meeting tracked data in a call, which is hooked. So a call from outside numpy that mixes the two
# is counted, once per process, and offline the upper bound is everything loaded (`plain_operand`, science's ruling on this
# gap): `loaded_not_used` becomes `unknown`, while what was never loaded stays `omitting`, and `complete` rests on the
# lower bound, which a loss cannot raise. numpy's own helper arrays inside its own functions do not count.
PLAIN_OPERAND = "plain_operand"
_NUMPY_INTERNAL = ("numpy", "icsa.instruments")


def _mixes_plain(values, depth: int) -> None:
    st = _STATE
    if st is None or PLAIN_OPERAND in st.counts:
        return
    # A masked array with no provenance is plain too: its data are an array nothing watches. scipy.stats.mstats gives one.
    plain = [v for v in values if isinstance(v, np.ndarray) and type(v) is not TArray and v.size > 1
             and (not isinstance(v, np.ma.MaskedArray) or _prov(v) is None)]
    if not plain:
        return
    try:
        f = sys._getframe(depth)
        mod = f.f_globals.get("__name__", "") or ""
        if mod.startswith("numpy.ma"):
            # A masked operand: who called the operator. numpy.ma's own plain arrays there are masks, not data.
            if all(v.dtype.kind == "b" for v in plain):
                return
            while mod.startswith("numpy.ma") and f.f_back is not None:
                f = f.f_back
                mod = f.f_globals.get("__name__", "") or ""
    except ValueError:
        return
    if not mod.startswith(_NUMPY_INTERNAL):
        st.count(PLAIN_OPERAND, where=f"{f.f_code.co_filename}:{f.f_lineno}", module=mod,
                 shape=list(plain[0].shape), dtype=plain[0].dtype.str)


def _flat_operands(x, out: list, depth: int = 0) -> list:
    """The arrays among a call's arguments: positional, by keyword, or in a list or tuple of them."""
    if isinstance(x, np.ndarray):
        out.append(x)
    elif isinstance(x, (list, tuple)) and depth < 3 and len(x) <= 256:
        for v in x:
            _flat_operands(v, out, depth + 1)
    elif isinstance(x, dict):
        for v in x.values():
            _flat_operands(v, out, depth + 1)
    return out


@_timed
def _ufunc(ufunc, method, inputs, kwargs):
    tracked = _collect(inputs, [])
    if tracked:
        _mixes_plain((*inputs, kwargs.get("where")), 4)    # _mixes_plain, _ufunc, the timer, __array_ufunc__, the caller
    out = kwargs.get("out")
    plain_kwargs = dict(kwargs)
    if out is not None:
        plain_kwargs["out"] = tuple(_unwrap(o) for o in (out if isinstance(out, tuple) else (out,)))
    if "where" in plain_kwargs:
        plain_kwargs["where"] = _unwrap(plain_kwargs["where"])
    r = _native(getattr(ufunc, method), *_unwrap(inputs), **plain_kwargs)
    if method == "at":
        # ufunc.at(a, indices, b) writes into a in place and returns None: a's values
        # (and those of every alias) now also depend on the other inputs, unmodelled.
        _mutated(inputs[0], [t for t in tracked if t is not inputs[0]])
        return r
    try:
        p = _ufunc_prov(ufunc, method, inputs, kwargs, r, tracked)
    except Exception:  # noqa: BLE001
        _count("internal_error")
        nd = r.ndim if isinstance(r, np.ndarray) else 0
        p = P.hi_only(P.union([t._p for t in tracked], nd), nd) if tracked else P.Prov.none()
    return _finish(r, p, out, kwargs.get("where", True) if method in ("__call__", "outer") else True)


_COMPARISONS = frozenset(("greater", "greater_equal", "less", "less_equal", "equal", "not_equal"))
DATA_COMPARISON = "data_comparison"


def _ufunc_prov(ufunc, method, inputs, kwargs, r, tracked):
    """The provenance of the computed values. where= on __call__ and outer is applied per output in _finish: those
    positions alone get them. On a reduction it decides which elements take part, so its units stay on record."""
    res = r[0] if isinstance(r, tuple) else r
    nd = np.ndim(res)
    shp = np.shape(res)
    wp = _prov(kwargs.get("where", True))
    if not tracked:
        return P.hi_only(wp, nd) if wp is not None and method == "reduce" else P.Prov.none()
    if ufunc.signature is not None:
        return P.hi_only(P.union([t._p for t in tracked], nd), nd)
    if method == "__call__":
        live = _tracked_inputs(inputs)
        parts = [P.broadcast(t._p, t.shape, shp) for t in live]
        p = parts[0] if len(parts) == 1 else P.union(parts, nd)
        if len(live) > 1 and ufunc.__name__ in _COMPARISONS:
            # Data against something derived from data, not against a constant. It stays in the flags
            # through later arithmetic, so a selection's origin can be read offline.
            p = P.Prov(p.lo, p.hi, p.flags | {DATA_COMPARISON})
        return p
    x = inputs[0]
    xp = _prov(x)
    if xp is None:
        return P.Prov.none()
    xs = np.shape(x)
    if method == "reduce":
        if kwargs.get("where", True) is not True:
            return P.hi_only(P.union([xp] + ([wp] if wp is not None else []), nd), nd)
        axis = kwargs.get("axis", 0)
        return P.reduce(xp, xs, axis, kwargs.get("keepdims", False))
    if method == "accumulate":
        axis = kwargs.get("axis", 0)
        return P.Prov(xp.lo, P.mix_axis(xp, xs, axis).hi, xp.flags)
    if method == "outer":
        a, b = inputs[0], inputs[1]
        parts = []
        if _prov(a) is not None:
            parts.append(P.reshape(_prov(a), np.shape(a), np.shape(a) + (1,) * np.ndim(b)))
            parts[-1] = P.broadcast(parts[-1], np.shape(a) + (1,) * np.ndim(b), shp)
        if _prov(b) is not None:
            q = P.broadcast(_prov(b), np.shape(b), shp)
            parts.append(q)
        return P.union(parts, nd)
    return P.hi_only(P.union([t._p for t in tracked], nd), nd)


def _tracked_inputs(inputs):
    out = []
    for x in inputs:
        if isinstance(x, (TArray, *_TSCALARS)) and not x._p.is_empty():
            out.append(x)
        elif isinstance(x, np.ma.MaskedArray) and isinstance(x._data, TArray) and not x._data._p.is_empty():
            out.append(x._data)
    return out


def _partial_write(p, where, old, shp):
    """A ufunc with where=: np.where(where, computed, out's old values), the rule of `_where`. Positions left out keep
    `old` (uninitialised if there is no out=, or if it was untracked: no provenance)."""
    cv = np.broadcast_to(np.asarray(_unwrap(where), bool), shp)
    wp = _prov(where)
    return _select(wp, np.shape(where), cv, [(p, shp, True), (old, shp, False)], shp)


def _finish(r, p, out, where):
    outs = None if out is None else (out if isinstance(out, tuple) else (out,))
    if isinstance(r, tuple):
        return tuple(_finish_one(x, p, outs[n] if outs is not None and n < len(outs) else None, where)
                     for n, x in enumerate(r))
    return _finish_one(r, p, outs[0] if outs else None, where)


def _finish_one(x, p, o, where):
    if where is not True:
        old = _prov(o) if o is not None else None
        try:
            p = _partial_write(p, where, old, np.shape(x))
        except Exception:  # noqa: BLE001
            _count("internal_error")
            nd = np.ndim(x)
            p = P.hi_only(P.union([p] + [q for q in (old, _prov(where)) if q is not None], nd), nd)
    if o is not None:
        # numpy wrote into `o` and returns it: keep its identity, update its provenance.
        if isinstance(o, TArray):
            o._p = p
            _invalidate(o, p)
            return o
        if isinstance(o, np.ma.MaskedArray):
            _set_ma_prov(o, p)
            _invalidate(o, p)
            return o
        _escape_prov(p, "out_plain")
        return o
    if isinstance(x, np.ndarray):
        return _wrap(x, p)
    return _scalar(x, p)


# --------------------------------------------------------------- functions

_REDUCERS = {
    "sum": 1, "prod": 1, "mean": 1, "nanmean": 1, "nansum": 1, "nanprod": 1, "std": 1, "var": 1,
    "nanstd": 1, "nanvar": 1, "min": 1, "max": 1, "amin": 1, "amax": 1, "nanmin": 1, "nanmax": 1,
    "median": 1, "nanmedian": 1, "any": 1, "all": 1, "count_nonzero": 1, "ptp": 1,
    "argmax": 1, "argmin": 1, "nanargmax": 1, "nanargmin": 1, "average": 1,
    "percentile": 2, "nanpercentile": 2, "quantile": 2, "nanquantile": 2,
}
_SAME_SHAPE = {"copy", "nan_to_num", "round", "around", "real", "imag", "fix", "asfarray",
               "ascontiguousarray", "asfortranarray", "require", "array_equal"}
_EMPTY_LIKE = {"zeros_like", "ones_like", "empty_like", "full_like"}
# Functions that read only metadata (shape, dtype, memory layout), never values.
_METADATA = {"shape", "ndim", "size", "result_type", "iscomplexobj", "isrealobj", "may_share_memory",
             "shares_memory", "min_scalar_type", "can_cast", "common_type", "isfortran", "alen"}
_NOT = object()   # "no model": fall back to the generic rule


def _arg(args, kwargs, pos, name, default=None):
    if name in kwargs:
        return kwargs[name]
    if len(args) > pos:
        return args[pos]
    return default


@_timed
def _function(func, args, kwargs, call=None):
    """`call`: how to run the function (masked arrays: numpy's own dispatch, hooks.py);
    default: on the unwrapped arguments."""
    name = getattr(func, "__name__", "")
    res = _function_call(func, name, args, kwargs, call)
    if name in _OVERWRITE_INPUT:
        # overwrite_input=True partitions the input in place: its elements (and those of every view of it) have moved
        # along the axis, so nothing about any one position holds. The result, taken above, is not affected.
        b = _bound(func, args, kwargs)
        if b is None:
            _count("internal_error")
        elif b.get("overwrite_input"):
            _mutated(b["a"], _collect(b["a"], []))
    return res


def _function_call(func, name, args, kwargs, call):
    run0 = call or (lambda: func(*_unwrap(args), **_unwrap(kwargs)))

    def run():
        return _native(run0)
    if name in _METADATA:
        return run()
    tracked = _collect((args, kwargs), [])
    if tracked:
        _mixes_plain(_flat_operands((args, kwargs), []), 5)  # _mixes_plain, _function_call, _function, the timer, __array_function__, the caller
    if name == "copyto":
        run()
        try:
            _copyto(args, kwargs)
        except Exception:  # noqa: BLE001
            _count("internal_error")
            if isinstance(args[0], TArray):
                args[0]._p = P.hi_only(P.union([t._p for t in tracked], args[0].ndim), args[0].ndim)
        return None
    r = run()
    if name in _INPLACE_FIRST:
        # numpy functions that write into their first parameter (positional or keyword):
        # its values (and those of every alias) now also depend on the other inputs.
        dst = _first_param(func, args, kwargs)
        if dst is not None:
            _mutated(dst, [t for t in tracked if t is not dst])
        return r
    outs = _outs(func, args, kwargs, r)
    if not tracked and name not in _EMPTY_LIKE:
        for o in outs:
            _mutated(o, [], overwrite=True)
        # stays a tracked-type array with nothing in it, as a ufunc's result does: a later write into it is seen, and it
        # is no plain operand
        return _wrap(r, P.Prov.none()) if type(r) is np.ndarray else r
    res = _NOT
    try:
        # A where= mask leaves positions out of the computation; only the functions with
        # their own rule (np.where's condition, copyto, above) keep a lower bound under it.
        if _where_arg(func, args, kwargs) is not True:
            pass
        elif not outs or (name in _REDUCERS and "out" in kwargs and len(outs) == 1 and outs[0] is kwargs["out"]):
            res = _function_result(func, name, args, kwargs, r, tracked)
    except Exception:  # noqa: BLE001
        _count("internal_error")
    if res is not _NOT:
        for o in outs:      # a modelled write into out=: its new provenance is set; aliases are stale
            if isinstance(o, TArray):
                _invalidate(o, o._p)
            elif isinstance(o, np.ma.MaskedArray) and _ma_prov(o) is not None:
                _invalidate(o, _ma_prov(o))
            else:
                _mutated(o, tracked, overwrite=True)
        return res
    if res is _NOT:
        if _DEBUG:
            print(f"[icsa tracer] unmodelled function {getattr(func, '__module__', '')}.{name}", file=sys.stderr)
        res = _generic(r, tracked)
        for o in outs:      # an unmodelled write into out=: lo dropped, hi = all inputs
            _mutated(o, tracked, overwrite=True)
    return res


# numpy functions (dispatched through __array_function__) that write into args[0].
_INPLACE_FIRST = frozenset({"putmask", "place", "put", "put_along_axis", "fill_diagonal"})
# numpy functions that rearrange their first parameter when told they may.
_OVERWRITE_INPUT = frozenset({"median", "nanmedian", "percentile", "nanpercentile", "quantile", "nanquantile"})


_SIGS: dict = {}


def _bound(func, args, kwargs) -> dict | None:
    """The call's arguments by parameter name, or None if the signature is unknown."""
    key = id(func)
    if key not in _SIGS:
        try:
            _SIGS[key] = inspect.signature(func)
        except (TypeError, ValueError):
            _SIGS[key] = None
    sig = _SIGS[key]
    if sig is None:
        return None
    names = _POSITIONAL.get(key)
    if names is None:
        ps = list(sig.parameters.values())
        simple = all(p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY) for p in ps)
        names = _POSITIONAL[key] = (tuple(p.name for p in ps if p.kind != p.KEYWORD_ONLY) if simple else ())
    if names and len(args) <= len(names) and not any(k in names[:len(args)] for k in kwargs) \
            and all(k in sig.parameters for k in kwargs):
        # what bind_partial gives for a plain call, without binding (a loop calls this per element)
        d = dict(zip(names, args))
        d.update(kwargs)
        return d
    try:
        return dict(sig.bind_partial(*args, **kwargs).arguments)
    except TypeError:
        return None


_POSITIONAL: dict = {}


def _where_arg(func, args, kwargs):
    w = kwargs.get("where", True)
    if w is True and len(args) > 3:
        b = _bound(func, args, kwargs)
        w = b.get("where", True) if b else True
    return w


def _first_param(func, args, kwargs):
    if args:
        return args[0]
    b = _bound(func, args, kwargs)
    if b:
        return next(iter(b.values()))
    return next(iter(kwargs.values()), None)


def _outs(func, args, kwargs, r) -> list:
    """Destinations the call wrote into: out= by keyword or by position (from the
    signature), and any positional array the function returned as its result."""
    cands = []
    o = kwargs.get("out")
    b = None
    if o is None and len(args) > 1:
        b = _bound(func, args, kwargs)
        o = b.get("out") if b else None
    if o is not None:
        cands += list(o) if isinstance(o, tuple) else [o]
    if b is None and o is None and len(args) > 1 and _SIGS.get(id(func), 0) is None:
        # No signature to read out= from: a positional array the function returned is
        # taken as its out (the function ran on unwrapped arguments, so match by memory).
        rs = [y for y in (r if isinstance(r, tuple) else (r,)) if isinstance(y, np.ndarray)]
        cands += [x for x in args[1:] if isinstance(x, np.ndarray)
                  and any(_same_elements(_plain(x) if isinstance(x, TArray) else x, y) for y in rs)]
    out, seen = [], set()
    for x in cands:
        if isinstance(x, np.ndarray) and id(x) not in seen:
            seen.add(id(x))
            out.append(x)
    return out


def _mutated(dst, sources, overwrite=False):
    """dst was written by an unmodelled operation from `sources` (tracked arrays):
    its lo is dropped, its hi keeps what it had (unless overwritten) plus the sources,
    and every other live alias of its buffer is invalidated the same way."""
    try:
        vp = P.union([t._p for t in sources], np.ndim(dst)) if sources else None
        if isinstance(dst, TArray):
            parts = ([] if overwrite else [dst._p]) + ([vp] if vp is not None else [])
            dst._p = P.hi_only(P.union(parts, dst.ndim), dst.ndim) if parts else P.Prov.none()
        elif isinstance(dst, np.ma.MaskedArray):
            old = _ma_prov(dst)
            parts = ([] if overwrite or old is None else [old]) + ([vp] if vp is not None else [])
            _set_ma_prov(dst, P.hi_only(P.union(parts, dst.ndim), dst.ndim) if parts else P.Prov.none())
        elif vp is not None:
            # tracked values written into an untracked array leave tracking here
            _escape_prov(vp, "into_plain")
        _invalidate(dst, vp)
    except Exception:  # noqa: BLE001
        _count("internal_error")


def _generic(r, tracked):
    def one(x):
        if isinstance(x, np.ndarray):
            return _wrap(x, P.hi_only(P.union([t._p for t in tracked], x.ndim), x.ndim))
        if isinstance(x, (tuple, list)):
            return type(x)(one(v) for v in x)
        # Anything else (a scalar, a string, None from a writer such as np.save or
        # np.savetxt): the values may have left tracking through the result or a side
        # effect, so the inputs escape.
        _escape_prov(P.union([t._p for t in tracked], 0), "unmodelled_result")
        return x
    _count("unmodelled")
    return one(r)


def _ret(r, p):
    if isinstance(r, np.ndarray):
        return _wrap(r, p)
    return _scalar(r, p)


def _function_result(func, name, args, kwargs, r, tracked):
    a0 = args[0] if args else None
    if name in _EMPTY_LIKE:
        if name == "full_like":             # the prototype gives only a shape and a type; the fill value is a value
            fill = _arg(args, kwargs, 1, "fill_value")
            fp = _prov(fill)
            if fp is not None and not fp.is_empty():
                return _ret(r, P.broadcast(fp, np.shape(fill), np.shape(r)))
        return _wrap(r, P.Prov.none()) if isinstance(r, np.ndarray) else r
    if name in _REDUCERS:
        p0 = _prov(a0)
        if p0 is None or len(tracked) != 1:
            return _NOT
        if _arg(args, kwargs, 99, "where", True) is not True or _arg(args, kwargs, 99, "weights") is not None:
            return _NOT
        if name == "average" and len(args) > 2:
            return _NOT
        axis = _arg(args, kwargs, _REDUCERS[name], "axis")
        keep = bool(kwargs.get("keepdims", False))
        red = P.reduce(p0, np.shape(a0), axis, keep)
        if _REDUCERS[name] == 2:
            q = _arg(args, kwargs, 1, "q")
            qn = np.ndim(q)
            if qn:
                rs = np.shape(r)[qn:]
                red = P.broadcast(red, rs, np.shape(r))
        out = kwargs.get("out")
        if out is not None and isinstance(out, TArray):
            out._p = red
            _invalidate(out, red)
            return out
        return _ret(r, red)
    if name in _SAME_SHAPE:
        p0 = _prov(a0)
        if p0 is None or len(tracked) != 1 or np.shape(r) != np.shape(a0):
            return _NOT
        return _ret(r, p0)
    if name == "clip":
        shp = np.shape(r)
        parts = [P.broadcast(_prov(x), np.shape(x), shp) for x in (a0, _arg(args, kwargs, 1, "a_min"),
                                                                    _arg(args, kwargs, 2, "a_max"))
                 if _prov(x) is not None]
        return _ret(r, P.union(parts, len(shp)))
    if name == "where":
        if len(args) == 1:
            return _nonzero_result(a0, r)
        return _where(args, r)
    if name in ("nonzero", "argwhere", "flatnonzero"):
        res = _nonzero_result(a0, r if name == "nonzero" else np.nonzero(_unwrap(a0)))
        if name == "nonzero":
            return res
        p = P.union([_prov(x) for x in res], 1)
        if name == "argwhere":
            p = P.broadcast(P.reshape(p, (len(res[0]),), (len(res[0]), 1)), (len(res[0]), 1), np.shape(r))
            return _wrap(r, p) if np.ndim(a0) else None
        return _wrap(r, p)
    if name in ("transpose", "moveaxis", "swapaxes", "squeeze", "expand_dims", "ravel", "reshape",
                "atleast_1d", "atleast_2d", "atleast_3d", "broadcast_to", "flip", "flipud", "fliplr",
                "take", "roll", "diff", "sort", "argsort", "cumsum", "cumprod", "nancumsum", "nancumprod",
                "pad", "repeat"):
        if len(tracked) != 1 or _prov(a0) is None:
            return _NOT
        return _shape_fn(name, a0, args, kwargs, r)
    if name in ("concatenate", "stack", "vstack", "hstack", "dstack", "column_stack", "append"):
        return _concat_fn(name, args, kwargs, r)
    if name in ("split", "array_split", "hsplit", "vsplit", "dsplit"):
        return _NOT
    if name == "sliding_window_view":
        return _window(a0, args, kwargs, r)
    return _NOT


def _where(args, r):
    cond, x, y = args[0], args[1], args[2]
    shp = np.shape(r)
    cv = np.broadcast_to(np.asarray(_unwrap(cond), bool), shp)
    return _wrap(r, _select(_prov(cond), np.shape(cond), cv, [(_prov(x), np.shape(x), True), (_prov(y), np.shape(y), False)], shp))


def _select(cp, cshape, cv, branches, shp) -> P.Prov:
    """The provenance of elements each taken from one branch by a condition with values `cv` and provenance `cp`."""
    nd = len(shp)
    parts_hi, lo = [], []
    if cp is not None:
        cb = P.broadcast(cp, cshape, shp)
        parts_hi.append(cb)
        lo += cb.lo
    for bp, bshape, val in branches:
        if bp is None:
            continue
        bb = P.broadcast(bp, bshape, shp)
        sel = cv if val else ~cv
        if sel.all():
            parts_hi.append(bb)
            lo += bb.lo
            continue
        if not sel.any():
            continue                       # this branch was never selected
        # The branch counts only where it was selected: exact when the condition
        # varies along one axis only; otherwise lo drops it and hi keeps all of it.
        for k in range(nd):
            other = tuple(a for a in range(nd) if a != k)
            anyk, allk = sel.any(axis=other), sel.all(axis=other)
            if np.array_equal(anyk, allk):
                pos = np.nonzero(anyk)[0]
                key = tuple(pos if a == k else slice(None) for a in range(nd))
                q, _ = P.getitem(bb, shp, key)
                placed = P.setitem(P.Prov.none(), shp, key, q, q_shape(shp, k, len(pos)))
                parts_hi.append(placed)
                lo += placed.lo
                break
        else:
            parts_hi.append(bb)
    hi = P.union(parts_hi, nd)
    return P.Prov(P.merge(lo), hi.hi, hi.flags)


def q_shape(shp, k, n):
    s = list(shp)
    s[k] = n
    return tuple(s)


def _nonzero_result(a0, r):
    p0 = _prov(a0)
    if p0 is None:
        return _NOT
    mask = np.asarray(_unwrap(a0), bool)
    if mask.ndim == 0:
        return _NOT
    q, _ = P.getitem(p0, mask.shape, (mask,))
    hi = P.Prov((), (P.collapse(p0.hi, 1),)) if p0.hi else P.Prov.none()
    pr = P.Prov(q.lo, P.union([q, hi], 1).hi, q.flags)
    return tuple(_wrap(x, pr) for x in r)


def _shape_fn(name, a0, args, kwargs, r):
    p0, s0 = _prov(a0), np.shape(a0)
    shp = np.shape(r)
    nd = len(shp)
    if name in ("reshape", "ravel", "squeeze", "expand_dims", "atleast_1d", "atleast_2d", "atleast_3d"):
        if name == "atleast_3d" and len(s0) < 3:
            return _NOT
        if name in ("reshape", "ravel"):
            order = _arg(args, kwargs, 2 if name == "reshape" else 1, "order", "C")
            c_like = order == "C" or (order in ("A", "K") and np.asarray(_unwrap(a0)).flags.c_contiguous)
            if not c_like:
                return _NOT
        return _ret(r, P.reshape(p0, s0, shp))
    if name in ("transpose", "moveaxis", "swapaxes"):
        if name == "transpose":
            axes = _arg(args, kwargs, 1, "axes")
            perm = tuple(range(len(s0)))[::-1] if axes is None else tuple(a % len(s0) for a in axes)
        else:
            perm = tuple(range(len(s0)))
            src = _arg(args, kwargs, 1, "source" if name == "moveaxis" else "axis1")
            dst = _arg(args, kwargs, 2, "destination" if name == "moveaxis" else "axis2")
            if name == "swapaxes":
                lst = list(perm)
                a, b = src % len(s0), dst % len(s0)
                lst[a], lst[b] = lst[b], lst[a]
                perm = tuple(lst)
            else:
                srcs = [s % len(s0) for s in np.atleast_1d(src)]
                dsts = [d % len(s0) for d in np.atleast_1d(dst)]
                order = [n for n in range(len(s0)) if n not in srcs]
                for d, s in sorted(zip(dsts, srcs)):
                    order.insert(d, s)
                perm = tuple(order)
        return _ret(r, P.transpose(p0, perm))
    if name == "broadcast_to":
        return _ret(r, P.broadcast(p0, s0, shp))
    if name in ("flip", "flipud", "fliplr"):
        axis = 0 if name == "flipud" else 1 if name == "fliplr" else _arg(args, kwargs, 1, "axis")
        axes = range(len(s0)) if axis is None else np.atleast_1d(axis)
        key = [slice(None)] * len(s0)
        for a in axes:
            key[a % len(s0)] = slice(None, None, -1)
        q, _ = P.getitem(p0, s0, tuple(key))
        return _ret(r, q)
    if name == "take":
        idx = _unwrap(_arg(args, kwargs, 1, "indices"))
        axis = _arg(args, kwargs, 2, "axis")
        mode = _arg(args, kwargs, 4, "mode", "raise")
        if axis is None or np.ndim(idx) > 1 or _arg(args, kwargs, 3, "out") is not None:
            return _NOT
        n = s0[axis % len(s0)]
        idx = np.asarray(idx, np.int64)
        idx = idx % n if mode == "wrap" else np.clip(idx, 0, n - 1) if mode == "clip" else np.where(idx < 0, idx + n, idx)
        key = tuple(idx if a == axis % len(s0) else slice(None) for a in range(len(s0)))
        q, s = P.getitem(p0, s0, key)
        return _ret(r, q) if s == shp else None
    if name == "roll":
        shift = _arg(args, kwargs, 1, "shift")
        axis = _arg(args, kwargs, 2, "axis")
        if axis is None or np.ndim(shift) or np.ndim(axis):
            return _NOT
        ax = axis % len(s0)
        idx = (np.arange(s0[ax]) - int(shift)) % s0[ax]
        key = tuple(idx if a == ax else slice(None) for a in range(len(s0)))
        q, _ = P.getitem(p0, s0, key)
        return _ret(r, q)
    if name == "diff":
        n = int(_arg(args, kwargs, 1, "n", 1))
        axis = _arg(args, kwargs, 2, "axis", -1) % len(s0)
        if "prepend" in kwargs or "append" in kwargs:
            return _NOT
        return _ret(r, P.shifted(p0, s0, axis, range(n + 1), shp[axis]))
    if name in ("sort", "argsort"):
        axis = _arg(args, kwargs, 1, "axis", -1)
        if axis is None:
            return _NOT
        return _ret(r, P.mix_axis(p0, s0, axis))
    if name in ("cumsum", "cumprod", "nancumsum", "nancumprod"):
        axis = _arg(args, kwargs, 1, "axis")
        if axis is None:
            return _NOT
        return _ret(r, P.Prov(p0.lo, P.mix_axis(p0, s0, axis).hi, p0.flags))
    if name == "pad":
        mode = _arg(args, kwargs, 2, "mode", "constant")
        if mode != "constant" or _collect(kwargs.get("constant_values"), []):
            return _NOT
        widths = np.broadcast_to(np.asarray(_arg(args, kwargs, 1, "pad_width")), (len(s0), 2))
        p = p0
        cur = s0
        for ax in range(len(s0)):
            b, e = int(widths[ax][0]), int(widths[ax][1])
            if b == e == 0:
                continue
            new = list(cur)
            new[ax] = cur[ax] + b + e
            key = tuple(slice(b, b + cur[ax]) if a == ax else slice(None) for a in range(len(cur)))
            p = P.setitem(P.Prov.none(), tuple(new), key, p, cur)
            cur = tuple(new)
        return _ret(r, p)
    return _NOT


def _concat_fn(name, args, kwargs, r):
    seq = list(args[0]) if args else list(kwargs.get("arrays", kwargs.get("tup", [])))
    if name == "append":
        seq = [args[0], args[1]]
        axis = _arg(args, kwargs, 2, "axis")
        if axis is None:
            return _NOT
    else:
        axis = _arg(args, kwargs, 1, "axis", 0)
    shp = np.shape(r)
    if name in ("vstack", "hstack", "dstack", "column_stack"):
        return _NOT if name != "vstack" or any(np.ndim(x) != len(shp) for x in seq) else \
            _concat_parts(seq, 0, shp, r)
    if name == "stack":
        ax = axis % len(shp)
        parts, shapes = [], []
        for x in seq:
            s = np.shape(x)
            ns = s[:ax] + (1,) + s[ax:]
            p = _prov(x)
            parts.append(P.reshape(p, s, ns) if p is not None else P.Prov.none())
            shapes.append(ns)
        return _ret(r, P.concatenate(parts, shapes, ax))
    if axis is None:
        return _NOT
    return _concat_parts(seq, axis, shp, r)


def _concat_parts(seq, axis, shp, r):
    parts, shapes = [], []
    for x in seq:
        p = _prov(x)
        parts.append(p if p is not None else P.Prov.none())
        shapes.append(np.shape(x))
    if any(len(s) != len(shp) for s in shapes):
        return _NOT
    return _ret(r, P.concatenate(parts, shapes, axis % len(shp)))


def _window(a0, args, kwargs, r):
    p0, s0 = _prov(a0), np.shape(a0)
    w = _arg(args, kwargs, 1, "window_shape")
    axis = _arg(args, kwargs, 2, "axis")
    if p0 is None or np.ndim(w) or axis is None or np.ndim(axis):
        return _NOT
    w = int(w)
    ax = axis % len(s0)
    n = s0[ax] - w + 1
    shp = np.shape(r)
    parts = []
    for o in range(w):
        key = tuple(slice(o, o + n) if a == ax else slice(None) for a in range(len(s0)))
        q, qs = P.getitem(p0, s0, key)
        q = P.reshape(q, qs, qs + (1,))
        key2 = (slice(None),) * len(qs) + (o,)
        parts.append(P.setitem(P.Prov.none(), shp, key2, P.reshape(q, qs + (1,), qs), qs))
    return _ret(r, P.union(parts, len(shp)))


def _copyto(args, kwargs):
    dst, src = args[0], args[1]
    where = _arg(args, kwargs, 3, "where", True)
    if isinstance(dst, np.ma.MaskedArray):
        v = np.ndarray.view(dst, TArray)        # the same elements: model on the view
        v._p = _ma_prov(dst) or P.Prov.none()
        _copyto((v,) + tuple(args[1:]), kwargs)
        _set_ma_prov(dst, v._p)
        return None
    if not isinstance(dst, TArray):
        if _collect((src, where), []):
            _escape_prov(P.union([t._p for t in _collect((src, where), [])], np.ndim(dst)), "copyto_plain")
        return None
    shp = dst.shape
    sp = _prov(src)
    sb = P.broadcast(sp, np.shape(src), shp) if sp is not None else P.Prov.none()
    if where is True:
        dst._p = sb
        _invalidate(dst, sb)
        return None
    wp = _prov(where)
    parts = [dst._p, sb] + ([P.broadcast(wp, np.shape(where), shp)] if wp is not None else [])
    hi = P.union(parts, len(shp))
    lo = P.broadcast(wp, np.shape(where), shp).lo if wp is not None else ()
    dst._p = P.Prov(lo, hi.hi, hi.flags | {"lo_dropped"})
    _invalidate(dst, hi)
    return None


# --------------------------------------------------------------- the state

def _caller_module(depth=2) -> str:
    try:
        f = sys._getframe(depth)
    except ValueError:
        return ""
    return f.f_globals.get("__name__", "") or ""


_LIB_FILE_CACHE: dict[str, bool] = {}


def _is_lib_file(fn: str) -> bool:
    """Whether code from file `fn` is library code: a frozen module, or an existing
    file under a library directory. The directories end with a separator, so
    `<prefix>-agent/x.py` is not under `<prefix>`; a made-up filename (compile(...,
    "<site-packages>/fake.py")) is not a library file because it does not exist."""
    v = _LIB_FILE_CACHE.get(fn)
    if v is None:
        if fn.startswith("<frozen"):
            v = True
        elif fn.startswith("<"):
            v = False
        else:
            v = ((fn.startswith(_LIB_PREFIXES) or os.path.realpath(fn).startswith(_LIB_PREFIXES))
                 and os.path.isfile(fn))
        _LIB_FILE_CACHE[fn] = v
    return v


def _is_agent_frame(depth=2) -> bool:
    try:
        f = sys._getframe(depth)
    except ValueError:
        return False
    return not _is_lib_file(f.f_code.co_filename)


_seq_lock = threading.Lock()
_seq = [0]


class _LogFull(Exception):
    """The escape budget is spent: the record is dropped and `escape_log_full` stands for it."""


def next_seq() -> int:
    """One order over the sink writes and the escape events of a process."""
    with _seq_lock:
        _seq[0] += 1
        return _seq[0]


_ORPHANED_STREAMS: list = []         # a fork's copies of the parent's open files (Tracer.after_fork)

# Of /trace's 256 MiB. Past either, the rest is not recorded and the run's upper bound is H = L (`escape_log_full`).
MAX_ESCAPE_BYTES = 64 * 2**20
MAX_SCALAR_BYTES = 64 * 2**20
MAX_CONSTANT_WRITE_BYTES = 64 * 2**20
MAX_VALUES = 4096       # a selection (bool or int) up to this size is recorded with its values


class Tracer:
    def __init__(self, trace_dir: Path, output_dir: Path | None):
        self.dir = Path(trace_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.out = Path(output_dir).resolve() if output_dir else None
        self.pid = os.getpid()
        self.lock = threading.RLock()
        self.files: dict[str, int] = {}
        self.counts: dict[str, int] = {}
        self.seen: weakref.WeakSet = weakref.WeakSet()     # provenances already escaped
        self.seq = 0
        self._fh = {}
        self.t0 = time.time()
        self._set_ids: set[str] = set()     # per-dimension sets already written (content-addressed)
        self._escape_bytes = 0
        self._escape_full = False
        self._scalar_bytes = 0
        self._scalar_recent: dict[tuple, None] = {}
        self._write_bytes = 0
        self._write_full = False
        # A write that fails (a full /trace, a file-size limit, a closed descriptor) must never reach the agent's
        # code, where it would look like a data error. The first failure stops this process's trace and removes
        # its `ok` marker (an unlink needs no space); offline, a started process without its marker makes the run
        # unknown (`trace_write_failed`). A process that is killed keeps its marker: its lines up to then stand.
        self.failed: str | None = None
        self.marker = self.dir / f"ok.{self.pid}"
        try:
            self.marker.touch()
            self.marker_ok = True
        except OSError:
            self.marker_ok = False
        self._aids: dict[int, int] = {}     # buffer owner -> a number for the records (constant writes)
        self._ref_cache: dict = {}
        self._col_cache: dict = {}
        self.loaded: dict | None = None     # what instrument-loaded says (write_loaded); a fork repeats it

    def after_fork(self) -> None:
        """This process is a fork of the one that made this object. It gets its own lock, marker and streams, named by
        its own pid; analyse keeps a table of file numbers per process, and arrays inherited from the parent carry the
        parent's numbers, so its stream repeats the table so far and new files continue from there. The parent's open
        streams are kept, never closed here: each holds complete lines, and another thread may have been writing one."""
        parent, self.lock = self.pid, threading.RLock()
        _ORPHANED_STREAMS.extend(self._fh.values())
        self._fh = {}
        self.pid = os.getpid()
        self.counts = {}                    # the parent's own stand in the parent's stream
        self._scalar_recent = {}
        self.marker = self.dir / f"ok.{self.pid}"
        if self.failed is None:
            try:
                self.marker.touch()
                self.marker_ok = True
            except OSError:
                self.marker_ok = False
        self.tt_write()
        for ident, fid in self.files.items():
            self._write("files", {"fid": fid, "ident": ident})
        self._write("events", {"t": time.time(), "kind": "start", "pid": self.pid, "forked_from": parent,
                               "ok_marker": self.marker_ok, "output_dir": str(self.out), "cell": cell_number(),
                               "ppid": os.getppid(), "ancestors": ancestors()})
        if self.loaded is not None:
            self.write_loaded(self.loaded["patches"])

    def write_loaded(self, patches: dict) -> None:
        """The positive record that the instrument is in place in this process (Tracer #6, science, #2): its absence,
        or ok false, makes the run invalid in the harness and unknown offline. Written whole under a temporary name,
        so a reader never takes a part of it for the record."""
        self.loaded = {"schema": 1, "pid": self.pid, "t": time.time(),
                       "ok": all(patches.values()) and self.marker_ok and self.failed is None,
                       "patches": dict(patches), "marker_ok": self.marker_ok, "cell": cell_number()}
        path = self.dir / f"instrument-loaded.{self.pid}.json"
        tmp = self.dir / f".instrument-loaded.{self.pid}.tmp"
        try:
            tmp.write_text(json.dumps(self.loaded, separators=(",", ":")))
            os.replace(tmp, path)
        except Exception as e:  # noqa: BLE001 - never into agent code; no record, so the run is invalid
            self._fail(e)

    def _write(self, stream: str, rec: dict):
        self._write_line(stream, json.dumps(rec, separators=(",", ":")))

    def _write_line(self, stream: str, line: str):
        with self.lock:
            if self.failed is not None:
                return
            try:
                fh = self._fh.get(stream)
                if fh is None:
                    fh = open(self.dir / f"{stream}.{self.pid}.jsonl", "a", buffering=1)
                    self._fh[stream] = fh
                fh.write(line + "\n")
            except Exception as e:  # noqa: BLE001 - never into agent code
                self._fail(e)

    def _fail(self, e: BaseException) -> None:
        self.failed = f"{type(e).__name__}:{getattr(e, 'errno', None)}"
        try:
            os.unlink(self.marker)
        except OSError:
            pass
        for fh in self._fh.values():
            try:
                fh.close()
            except Exception:  # noqa: BLE001
                pass
        self._fh.clear()

    def _set_ref(self, rle: list) -> list | str:
        """A dimension's set in an escape event: a single value inline (that is what shows the event is
        aligned with one cell), anything else once, by its digest (a per-cell loop repeats one day set)."""
        if len(rle) == 1 and rle[0][1] - rle[0][0] == 1:
            return rle
        text = json.dumps(rle, separators=(",", ":"))
        ref = hashlib.blake2b(text.encode(), digest_size=8).hexdigest()
        if ref not in self._set_ids:
            line = '{"kind":"set","id":"%s","rle":%s}' % (ref, text)
            if self._escape_full or self._escape_bytes + len(line) + 1 > MAX_ESCAPE_BYTES:
                self._full()
                raise _LogFull
            self._set_ids.add(ref)
            self._escape_bytes += len(line) + 1
            self._write_line("events", line)
        return ref

    def _full(self) -> None:
        if not self._escape_full:
            self._escape_full = True
            self._write_line("events", '{"kind":"escape_log_full","seq":%d}' % next_seq())

    def escape(self, kind: str, how: str, p: P.Prov, c: P.Term, shape, dt, value) -> None:
        """Record one escape, in program order: its type, the shape and dtype of what left, its provenance
        as per-dimension sets, its flags, and for a small bool or int selection its values. The content never
        decides `complete` by itself; it widens the upper bound and lets a rule on links be applied offline."""
        with self.lock:
            if self._escape_full:
                return
            if self._escape_bytes > MAX_ESCAPE_BYTES:
                self._full()
                return
            rec = {"t": round(time.time(), 3), "kind": kind, "how": how, "seq": next_seq(),
                   "sets": {d[0]: self._set_ref(_rle(r[:, 0])) for d, r in c.fixed}}
            if shape is not None:
                rec["shape"] = list(shape)
            if dt is not None:
                rec["dt"] = dt
            if p.flags:
                rec["flags"] = sorted(p.flags)
            if value is not None:
                rec["v"] = value
            line = json.dumps(rec, separators=(",", ":"))
            self._escape_bytes += len(line) + 1
            self._write_line("events", line)

    def _dim_ref(self, parts: list) -> list | str:
        """The record of one dimension's set, the union of `parts` (arrays of values). Remembered for parts
        that are columns of the same factor arrays (a loop's pool), so a loop pays for it once."""
        if all(len(a) == 1 for a in parts):
            v = int(parts[0][0])
            if all(int(a[0]) == v for a in parts):
                return [[v, v + 1]]
        key = tuple((id(a), len(a)) for a in parts)
        hit = self._ref_cache.get(key)
        if hit is not None and all(x is y for x, y in zip(hit[0], parts)):
            return hit[1]
        ref = self._set_ref(_rle(P._uniq(np.concatenate(parts)) if len(parts) > 1 else parts[0]))
        if len(self._ref_cache) >= 256:
            self._ref_cache.clear()
        self._ref_cache[key] = (list(parts), ref)
        return ref

    def scalar_refs(self, p: P.Prov) -> dict | None:
        """Per-dimension records of a 0-d provenance's units, from its terms' factors; None if a term has axes."""
        cols: dict[str, list] = {}
        for t in p.hi:
            if t.axes:
                return None
            for dims, rel in t.fixed:
                for k, d in enumerate(dims):
                    cols.setdefault(d, []).append(self._column(rel, k))
        return {d: self._dim_ref(v) for d, v in cols.items()}

    def _column(self, rel: np.ndarray, k: int) -> np.ndarray:
        """Column k of a factor, distinct values, remembered per factor array (one per pool in a loop)."""
        if len(rel) == 1:
            return rel[0, k:k + 1]
        key = (id(rel), k)
        hit = self._col_cache.get(key)
        if hit is not None and hit[0] is rel:
            return hit[1]
        col = P._uniq(rel[:, k])
        if len(self._col_cache) >= 256:
            self._col_cache.clear()
        self._col_cache[key] = (rel, col)
        return col

    def scalar_escape(self, c: P.Term | None, dt, refs: dict | None = None) -> None:
        """A floating scalar reduced from tracked data, in one short line: [seq, f, t, j, i, dtype]. A Python
        loop makes millions, and two in a row with the same units (a threshold and a climatology from one
        pool) make one line."""
        with self.lock:
            if self._escape_full:
                return
            if self._scalar_bytes > MAX_SCALAR_BYTES:
                self._full()
                return
            if refs is None:
                refs = {d[0]: self._set_ref(_rle(r[:, 0])) for d, r in c.fixed}
            if not all(d in refs for d in ("f", "t", "j", "i")):
                self._write_line("events", json.dumps({"kind": "escape", "how": "scalar", "seq": next_seq(),
                                                       "sets": refs, "dt": dt}, separators=(",", ":")))
                return
            key = tuple(json.dumps(refs[d], separators=(",", ":")) for d in ("f", "t", "j", "i"))
            if key in self._scalar_recent:
                return
            self._scalar_recent[key] = None
            if len(self._scalar_recent) > 64:
                del self._scalar_recent[next(iter(self._scalar_recent))]
            line = "[%d,%s,%s,%s,%s,%s]" % (next_seq(), *key, json.dumps(dt))
            self._scalar_bytes += len(line) + 1
            self._write_line("scalars", line)

    def aid(self, owner) -> int:
        """A number for a buffer, for the records of constant writes into it."""
        with self.lock:
            k = id(owner)
            n = self._aids.get(k)
            if n is None:
                n = self._aids[k] = next_seq()
                try:
                    weakref.finalize(owner, self._aids.pop, k, None)
                except TypeError:
                    pass
            return n

    def constant_write(self, aid: int, shape, key, value) -> None:
        """A write into a tracked array of something with no provenance: [seq, buffer, shape, key, value]."""
        with self.lock:
            if self._write_full:
                return
            if self._write_bytes > MAX_CONSTANT_WRITE_BYTES:
                self._write_full = True
                self._write_line("events", '{"kind":"constant_write_log_full","seq":%d}' % next_seq())
                return
            line = json.dumps([next_seq(), aid, list(shape), key, value], separators=(",", ":"))
            self._write_bytes += len(line) + 1
            self._write_line("cwrites", line)

    def file_id(self, ident: str) -> int:
        with self.lock:
            if ident not in self.files:
                self.files[ident] = len(self.files)
                self._write("files", {"fid": self.files[ident], "ident": ident})
            return self.files[ident]

    def count(self, key: str, **where):
        with self.lock:
            n = self.counts.get(key, 0)
            self.counts[key] = n + 1
            if n == 0:
                # At once: the final counts are written at exit, which a killed process, and a multiprocessing child
                # leaving by os._exit, never reach. Offline, what the rules ask is whether a count is above zero.
                if key == "internal_error":
                    where = {**where, **_error_where()}
                self._write("events", {"kind": "first_count", "key": key, **where})
        if _DEBUG and key in ("internal_error", "unmodelled"):
            import traceback
            print(f"[icsa tracer] {key}", file=sys.stderr)
            if sys.exc_info()[0] is not None:
                traceback.print_exc()
            else:
                traceback.print_stack(limit=6)

    def save_prov(self, prov: P.Prov, kind: str) -> str:
        with self.lock:
            self.seq += 1
            name = f"{kind}.{self.pid}.{self.seq:06d}.npz"
            if self.failed is not None:
                return name
        try:
            save_prov(self.dir / "prov" / name, prov)
        except Exception as e:  # noqa: BLE001 - never into agent code
            with self.lock:
                self._fail(e)
        return name

    def tt_write(self) -> None:
        """The tracer-time record, written in place: one fixed-size line (`ttime.<pid>.json`)."""
        with self.lock:
            if self.failed is not None:
                return
            try:
                pid = os.getpid()
                if getattr(self, "_tt_fd", None) is None or self._tt_pid != pid:
                    self._tt_fd = os.open(self.dir / f"ttime.{pid}.json", os.O_WRONLY | os.O_CREAT, 0o644)
                    self._tt_pid = pid
                rec = json.dumps({"pid": pid, "hook_wall_ns": _TT[0], "hook_calls": _TT[1], "work": P.budgeted(), "work_parts": P._PARTS, "limit": P.WORK_LIMIT,
                                  "process_cpu_ns": time.process_time_ns(), "t": round(time.time(), 3)},
                                 separators=(",", ":")).encode()
                os.pwrite(self._tt_fd, rec.ljust(255) + b"\n", 0)
            except Exception as e:  # noqa: BLE001 - never into agent code
                self._fail(e)

    def close(self):
        _shared_add()                       # what this process spent stays on the run's counter
        if _STOPPED_NOTE[0] is not None:
            _note_stopped()
        self.tt_write()
        with self.lock:
            self._write("events", {"t": time.time(), "kind": "counts", "counts": self.counts})
            for fh in self._fh.values():
                try:
                    fh.close()
                except Exception as e:  # noqa: BLE001 - a failed flush at exit
                    self._fail(e)
                    break
            self._fh.clear()


_DEBUG = os.environ.get("ICSA_TRACER_DEBUG") == "1"


def _error_where() -> dict:
    """What a tracer error was: its type, message and last line, for the record of its first occurrence."""
    et, ev, tb = sys.exc_info()
    if et is None:
        return {}
    while tb.tb_next is not None:
        tb = tb.tb_next
    return {"exc": et.__name__, "message": str(ev)[:200], "at": f"{os.path.basename(tb.tb_frame.f_code.co_filename)}:{tb.tb_lineno}"}


def cell_number() -> int | None:
    """The harness's number of this cell, from `ICSA_CELL`; null outside a recorded cell (the start probes), or if the
    agent's code started this process with its environment scrubbed. The labeller checks each recorded cell has a start."""
    v = os.environ.get("ICSA_CELL")
    return int(v) if v and v.isdigit() else None


def ancestors() -> list[int]:
    """This process's chain of parents, nearest first, from /proc: what lets a launch be matched to the start of what it
    launched without passing anything through the environment, which the launcher can scrub, and through a shell."""
    out: list[int] = []
    pid = os.getppid()
    try:
        while pid > 0 and len(out) < 32:
            out.append(pid)
            with builtins.open(f"/proc/{pid}/stat", "rb") as f:
                stat = f.read()
            pid = int(stat[stat.rindex(b")") + 2:].split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return out


def _count(key: str):
    if _STATE is not None:
        # A case the model does not express (an N-dimensional index, np.ix_): the handlers here keep the upper bound and drop
        # the lower, as for any unmodelled operation. It is not an error of the tracer, and says nothing lost.
        if key == "internal_error" and isinstance(sys.exc_info()[1], P._Unsupported):
            key = "unmodelled"
        _STATE.count(key)


# Each element access of one array would be its own event: these stay once per provenance. Whatever else
# escapes twice escapes in order, since which came last can matter offline.
_ONCE = frozenset(("scalar_index", "item", "scalar"))


def _values(x: np.ndarray):
    """What a small selection holds: True positions as runs for a bool array, the values for an int one."""
    if x.size > MAX_VALUES or x.ndim > 1 or x.dtype.kind not in "biu":
        return None
    v = np.ndarray.view(x, np.ndarray)
    if v.ndim == 0:
        return v.item()
    return _rle(np.flatnonzero(v)) if v.dtype.kind == "b" else v.tolist()


def _escape(x: TArray, kind: str):
    _escape_prov(x._p, kind, shape=_ND_SHAPE.__get__(x), dt=x.dtype.char, value=x)


@_timed
def _escape_prov(p: P.Prov | None, kind: str, observation=False, shape=None, dt=None, value=None):
    st = _STATE
    if st is None or p is None or p.is_empty():
        return
    selection = isinstance(value, np.ndarray) and value.dtype.kind in "biu" and value.size <= MAX_VALUES
    with st.lock:
        if p in st.seen and (kind in _ONCE or not selection):   # weakly held: an escape must not keep its terms alive
            return
        st.seen.add(p)
    if st._escape_full:
        return
    try:
        if kind == "scalar" and dt in ("d", "f"):
            with st.lock:
                refs = st.scalar_refs(p)
            if refs is not None:
                st.scalar_escape(None, dt, refs)
                return
        c = P.collapse(p.hi, 0)
        if c is None:
            return
        if kind == "scalar" and dt in ("d", "f"):
            st.scalar_escape(c, dt)
            return
        if selection:
            value = _values(value)
        elif kind == "scalar" and isinstance(value, (np.bool_, np.integer)):
            value = value.item()
        else:
            value = None
        st.escape("observation" if observation else "escape", kind, p, c, shape, dt, value)
    except _LogFull:
        pass
    except Exception:  # noqa: BLE001
        st.count("internal_error")


def _key_record(key, shape):
    """A write's key for the record: slices as [start, stop, step], integers as they are; an array as its size,
    with its positions when small."""
    def one(k, n):
        if isinstance(k, slice):
            return list(k.indices(n)) if n is not None else [k.start, k.stop, k.step]
        if isinstance(k, (int, np.integer)):
            return int(k)
        if k is Ellipsis:
            return "..."
        if k is None:
            return "new"
        a = np.ndarray.view(k, np.ndarray) if isinstance(k, np.ndarray) else np.asarray(k)
        return {"dt": a.dtype.char, "size": int(a.size), "tracked": _prov(k) is not None and not _prov(k).is_empty(),
                "v": _values(a)}
    items = key if isinstance(key, tuple) else (key,)
    if len(items) != len(shape) or any(k is Ellipsis or k is None for k in items):
        return [one(k, None) for k in items]
    return [one(k, n) for k, n in zip(items, shape)]


def _constant_write(x: TArray, key, value) -> None:
    """Record a write of something with no provenance into a tracked array, from the agent's own code: the
    array, the index or slice bounds, and the value (a small one, or the buffer it came from)."""
    st = _STATE
    if st is None:
        return
    try:
        vp = _prov(value)
        if (vp is not None and not vp.is_empty()) or not _is_agent_frame(3):   # the caller of __setitem__ or fill
            return
        if isinstance(value, np.ndarray):
            if type(value) is not TArray and value.size > 1 and PLAIN_OPERAND not in st.counts \
                    and (not isinstance(value, np.ma.MaskedArray) or _prov(value) is None):
                st.count(PLAIN_OPERAND)   # into a tracked or untracked array alike: it can hold what nothing named
            v = {"from": st.aid(_owner(value)), "shape": list(value.shape), "v": _values(value)}
        elif isinstance(value, (bool, np.bool_, int, np.integer)):
            v = bool(value) if isinstance(value, (bool, np.bool_)) else int(value)
        elif isinstance(value, (float, np.floating)):
            v = "float"
        else:
            v = type(value).__name__
        st.constant_write(st.aid(_owner(x)), _ND_SHAPE.__get__(x), _key_record(key, _ND_SHAPE.__get__(x)), v)
    except Exception:  # noqa: BLE001
        st.count("internal_error")


def _observe(x: TArray):
    _escape_prov(x._p, "print", observation=True, shape=_ND_SHAPE.__get__(x), dt=x.dtype.char)


def _rle(v: np.ndarray) -> list[list[int]]:
    v = P._uniq(np.asarray(v, np.int64))
    if not len(v):
        return []
    br = np.nonzero(np.diff(v) != 1)[0]
    starts = np.concatenate([[v[0]], v[br + 1]])
    ends = np.concatenate([v[br], [v[-1]]]) + 1
    return [[int(a), int(b)] for a, b in zip(starts, ends)]


# --------------------------------------------------------------- provenance across processes
# A process's file numbers mean nothing in another one, so what crosses names its files by identity, and the reader takes
# numbers of its own. Through a pickle it travels with the array (a Pool's workers, a pickle on disk); through np.save the
# file's fingerprint carries it (hooks.py). What cannot travel arrives as plain values, the escape on record.
MAX_PICKLED_PROV = 16 * 2**20


def files_of(p: P.Prov, st: "Tracer") -> dict[str, str]:
    """The identity of each file a provenance names, in this process's numbering."""
    names = {fid: ident for ident, fid in st.files.items()}
    return {str(f): names[f] for f in P.file_ids(p)}


def in_this_process(p: P.Prov, files: dict[str, str]) -> P.Prov:
    st = _STATE
    if not files or st is None:
        return p
    return P.remap_files(p, {int(f): st.file_id(ident) for f, ident in files.items()})


def _prov_for_pickle(p: P.Prov):
    st = _STATE
    if st is None or not OWN_FILES:
        return None
    t = _tt_enter()
    try:
        buf = io.BytesIO()
        save_prov(buf, p)
        if buf.tell() > MAX_PICKLED_PROV:
            _count("pickled_prov_too_big")
            return None
        return buf.getvalue(), files_of(p, st)
    except Exception:  # noqa: BLE001 - never into agent code; the values go as plain, the escape on record
        _count("pickled_prov_failed")
        return None
    finally:
        _tt_leave(t)


def _prov_from_pickle(blob: bytes, files: dict[str, str]) -> P.Prov | None:
    if _STATE is None:
        return None
    t = _tt_enter()
    try:
        return in_this_process(load_prov(io.BytesIO(blob)), files)
    except Exception:  # noqa: BLE001
        _count("internal_error")
        return None
    finally:
        _tt_leave(t)


def _rebuild_tracked(arr, blob, files):
    p = _prov_from_pickle(blob, files)
    return arr if p is None else _wrap(arr, p)


def _rebuild_masked(reduced, blob, files):
    func, args, state = reduced
    m = func(*args)
    m.__setstate__(state)
    p = _prov_from_pickle(blob, files)
    if p is None:
        return m
    # as the ledger makes one: data and mask carry the provenance
    d = _wrap(np.ndarray.view(np.asarray(m.data), np.ndarray), p)
    mask = m.mask
    if isinstance(mask, np.ndarray) and mask.shape == m.shape:
        mask = _wrap(np.ndarray.view(mask, np.ndarray), p)
    return np.ma.MaskedArray(d, mask=mask, fill_value=m.fill_value)


# --------------------------------------------------------------- what the agent's stderr shows

_TP_NAMES: list = []
_TP_NAME_OFFSET = 3 * ctypes.sizeof(ctypes.c_void_p)   # after the variable-size object's head
_shown: dict = {}


def _name_for_c(cls, name: bytes) -> None:
    """CPython's own messages ('x' object has no attribute, is not callable, unhashable type) print a type's C name. numpy's types
    are written 'numpy.ndarray' there and ours would be 'ndarray'; `__name__` reads another field, and stays 'ndarray'."""
    slot = ctypes.c_char_p.from_address(id(cls) + _TP_NAME_OFFSET)
    if slot.value == cls.__name__.encode():         # else the layout is not the one known here: the message stays
        slot.value = name
        _TP_NAMES.append(slot)                      # holds the bytes


def _is_own(filename) -> bool:
    return isinstance(filename, str) and filename.startswith(_OWN_DIR)


def _without_own_frames(tb):
    """The traceback the agent's code would have had, with no frame of the tracer's in it."""
    kept = []
    while tb is not None:
        if not _is_own(tb.tb_frame.f_code.co_filename):
            kept.append(tb)
        tb = tb.tb_next
    out = None
    for t in reversed(kept):
        out = types.TracebackType(out, t.tb_frame, t.tb_lasti, t.tb_lineno)
    return out


def _excepthook(tp, e, tb):
    seen, x = set(), e
    while x is not None and id(x) not in seen:
        seen.add(id(x))
        x.__traceback__ = _without_own_frames(x.__traceback__)
        for c in (x.__cause__, x.__context__):
            if c is not None and id(c) not in seen:
                c.__traceback__ = _without_own_frames(c.__traceback__)
        x = x.__cause__ or x.__context__
    sys.__excepthook__(tp, e, e.__traceback__)


def _warning_action(msg, module: str, lineno: int) -> str:
    text = str(msg.message)
    for action, m, cat, mod, ln in warnings.filters:
        if (m is None or m.match(text)) and issubclass(msg.category, cat) and (mod is None or mod.match(module)) \
                and (ln == 0 or ln == lineno):
            return action
    return warnings.defaultaction


def _hide_own_frames() -> None:
    """A traceback or a warning names the agent's own line, as it does untraced, not a line of the tracer's: the agent reads its
    stderr. A warning raised from a hook is attributed to the hook's frame by Python, and remembered there, so it would also
    show once for the whole run instead of once per line of the agent's: that memory moves here, by the agent's line."""
    _name_for_c(TArray, b"numpy.ndarray")
    _name_for_c(TFloat64, b"numpy.float64")
    _name_for_c(TFloat32, b"numpy.float32")
    sys.excepthook = _excepthook
    walk = traceback._walk_tb_with_full_positions

    def walk_tb_with_full_positions(tb, *a, **k):
        return ((f, pos) for f, pos in walk(tb, *a, **k) if not _is_own(f.f_code.co_filename))
    traceback._walk_tb_with_full_positions = walk_tb_with_full_positions
    plain_walk = traceback.walk_tb

    def walk_tb(tb):
        return ((f, n) for f, n in plain_walk(tb) if not _is_own(f.f_code.co_filename))
    traceback.walk_tb = walk_tb
    stack_walk = traceback.walk_stack

    def walk_stack(f):
        return ((x, n) for x, n in stack_walk(f if f is not None else sys._getframe(1)) if not _is_own(x.f_code.co_filename))
    traceback.walk_stack = walk_stack
    outer, inner = inspect.getouterframes, inspect.getinnerframes
    inspect.getouterframes = lambda frame, context=1: [i for i in outer(frame, context) if not _is_own(i.filename)]
    inspect.getinnerframes = lambda tb, context=1: [i for i in inner(tb, context) if not _is_own(i.filename)]
    thread_hook = threading.excepthook

    def excepthook(args):
        tb = _without_own_frames(args.exc_traceback)
        if args.exc_value is not None:
            args.exc_value.__traceback__ = tb
        thread_hook(threading.ExceptHookArgs((args.exc_type, args.exc_value, tb, args.thread)))
    threading.excepthook = excepthook
    show = warnings._showwarnmsg

    def _showwarnmsg(msg):
        if not _is_own(msg.filename):
            return show(msg)
        f = sys._getframe(1)
        while f is not None and not _is_own(f.f_code.co_filename):
            f = f.f_back
        version = 0         # Python's count of filter changes, which empties a registry: the one it just used holds the latest
        while f is not None and _is_own(f.f_code.co_filename):
            r = f.f_globals.get("__warningregistry__")
            if r:
                v = r.get("version")
                if isinstance(v, int) and v > version:
                    version = v
                r.clear()
            f = f.f_back
        if f is None:
            return show(msg)
        where, line, module = f.f_code.co_filename, f.f_lineno, f.f_globals.get("__name__", "")
        action = _warning_action(msg, module, line)
        text = str(msg.message)
        key = {"default": (text, msg.category, where, line), "module": (text, msg.category, module), "once": (text, msg.category)}.get(action)
        if action == "ignore":
            return None
        if action == "error":
            raise msg.message if isinstance(msg.message, Warning) else msg.category(text)
        if key is not None:
            key = (id(warnings.filters), len(warnings.filters), version, key)
            if key in _shown:
                return None
            _shown[key] = True
        return show(warnings.WarningMessage(msg.message, msg.category, where, line, msg.file, None, msg.source))
    warnings._showwarnmsg = _showwarnmsg


# --------------------------------------------------------------- the work budget

MEMORY_EVERY = 20_000_000       # work between two looks at the memory: about 10 s, and what can grow it fastest counts as work
TRACER_HEADROOM = 1 << 30       # [sandbox_limits] tracer_headroom_gib: the container's limit is the agent's allowance plus this
_BUDGET_LEFT = [float("inf")]   # the work this process may spend
_MEMORY = [None, None]          # file descriptor of the container's memory.stat, and the anon bytes at which tracking stops
_STOPPED_NOTE = [None, None]    # why it stopped and the anon bytes then, until that is on record


def _stop_tracking(why: str = "work") -> None:
    """The run has spent its budget, or the tracer would take memory the agent is allowed (DESIGN.md, "The work budget"). From here
    every array answers that it carries nothing, so its arithmetic costs what numpy costs, and what the records held is freed;
    types and values stay as they were. Reads stay on the ledger, so what was loaded is still known. Offline the label is `unknown`,
    reason `tracking_budget`, unless a required unit was never loaded."""
    P.STOPPED[0] = True
    _STOPPED_NOTE[:] = [why, _anon_bytes() if _MEMORY[0] is not None else None]
    none = P.Prov.none()
    answer = property(lambda self: none, lambda self, v: None)
    for c in (TArray, *_TSCALARS):
        c._p = answer
    P._UNION_CACHE.clear()
    P._UNION_CACHE_ROWS[0] = 0
    P._FULL.clear()             # maps whose index has 8 bytes for every position of an axis
    P._PRESENCE.clear()
    for refs in list(_ALIASES.values()):
        for r in list(refs.values()):
            x = r()
            if x is not None:
                x.__dict__.pop("_p", None)
    if _STATE is not None:
        _STATE.count("tracking_budget", t=time.time(), why=why, work=P.budgeted(), left=_BUDGET_LEFT[0], limit=P.WORK_LIMIT,
                     hook_wall_ns=_TT[0], process_cpu_ns=time.process_time_ns())
        _STATE.count(f"tracking_budget_{why}")      # firings per cell, by why, in the run's counts


def _note_stopped() -> None:
    """Once the hook that stopped has returned what it held: did the memory fall? On record, for science's check of the guard."""
    why, before = _STOPPED_NOTE
    _STOPPED_NOTE[0] = None
    gc.collect()
    _trim_heap()
    if _STATE is not None:
        _STATE._write("events", {"t": time.time(), "kind": "tracking_stopped", "why": why, "anon_before": before,
                                 "anon_after": _anon_bytes() if _MEMORY[0] is not None else None})


def _trim_heap() -> None:
    """What the stop freed is free in the allocator, not in the kernel's count: glibc returns only the top of its heap, and the
    tracer's many small arrays leave free chunks between live ones. malloc_trim(0) gives those pages back. Only after a stop; a
    libc without it keeps them. Never into agent code."""
    try:
        ctypes.CDLL(None).malloc_trim(0)
    except Exception:  # noqa: BLE001 - never into agent code
        pass


def _anon_bytes() -> int | None:
    try:
        for line in os.pread(_MEMORY[0], 8192, 0).split(b"\n"):
            if line.startswith(b"anon "):
                return int(line[5:])
    except (OSError, TypeError, ValueError):
        pass
    return None


_SHARED = [None, 0, None]     # the run's work counter (trace/work.total): its descriptor, what this process has added, its path
_SHARED_LOCK = threading.Lock()   # threads share the descriptor, and flock does not exclude them: this does


def _shared_open(path, child=False) -> None:
    """The run's one budget (science, #2, 18:49Z): every process of the run adds its work to one counter, under a lock, so forked
    workers together stop at the limit."""
    if _SHARED[0] is not None:
        try:
            os.close(_SHARED[0])
        except OSError:
            pass
    _SHARED[:] = [None, 0, path]
    if path is None:
        return
    try:
        _SHARED[0] = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)
    except OSError:
        _SHARED[0] = None


def _shared_add() -> int | None:
    """Adds this process's budgeted work not yet on the counter and returns the run's total; None without a counter."""
    with _SHARED_LOCK:
        fd = _SHARED[0]
        if fd is None:
            return None
        delta = P.budgeted() - _SHARED[1]
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                raw = os.pread(fd, 8, 0)
                total = (int.from_bytes(raw, "little") if len(raw) == 8 else 0) + delta
                os.pwrite(fd, total.to_bytes(8, "little"), 0)
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            return None
        _SHARED[1] += delta
        return total


def _remaining(total=None) -> int:
    return P.WORK_LIMIT - total if total is not None else _BUDGET_LEFT[0] - P.budgeted()


def _next_look(total=None) -> int:
    """Work until the next look: the sum of all kinds grows at least as fast as the budgeted kinds, and a quarter of what is left
    keeps several processes from passing the limit far between their looks."""
    return max(1, int(min(MEMORY_EVERY, _remaining(total) // 4)))


def _budget_check() -> None:
    """Called when the count passes its next mark. Counted work decides; the memory is looked at only every MEMORY_EVERY of it."""
    if P.STOPPED[0]:
        return
    total = _shared_add()
    if _remaining(total) < 0:
        return _stop_tracking("work")
    if _MEMORY[1] is not None:
        anon = _anon_bytes()
        if anon is not None and anon >= _MEMORY[1]:
            return _stop_tracking("memory")
    P._WORK[1] = P._WORK[0] + _next_look(total)


def _start_budget(trace_dir) -> None:
    """A run's budget is one, over its processes: what those before this one spent is in their time records."""
    spent = 0
    for f in Path(trace_dir).glob("ttime.*.json"):
        try:
            spent += int(json.loads(f.read_text()).get("work", 0))      # the budgeted kinds (merge rows and term work)
        except (OSError, ValueError, TypeError):
            pass
    P._PARTS[:] = [0, 0, 0]
    _shared_open(str(Path(trace_dir) / "work.total"))
    total = _shared_add()
    spent = max(spent, total or 0)
    _BUDGET_LEFT[0] = P.WORK_LIMIT - spent
    P._WORK[:] = [0, _next_look(total)]
    P._ON_OVER[0] = _budget_check
    try:
        with open("/sys/fs/cgroup/memory.max", "rb") as f:
            limit = f.read().strip()
        if limit.isdigit():
            _MEMORY[:] = [os.open("/sys/fs/cgroup/memory.stat", os.O_RDONLY | os.O_CLOEXEC), int(limit) - TRACER_HEADROOM]
    except (OSError, ValueError):
        pass
    if _BUDGET_LEFT[0] <= 0:
        _stop_tracking()


# --------------------------------------------------------------- serialisation

def save_prov(path, p: P.Prov) -> None:
    if isinstance(path, Path):
        path.parent.mkdir(parents=True, exist_ok=True)
    arrs: dict[str, np.ndarray] = {}
    meta = {"flags": sorted(p.flags), "lo": [], "hi": []}
    for side in ("lo", "hi"):
        for ti, t in enumerate(getattr(p, side)):
            tm = {"axes": [], "fixed": []}
            for ai, m in enumerate(t.axes):
                if m is None:
                    tm["axes"].append(None)
                else:
                    k = f"{side}{ti}a{ai}"
                    arrs[k + "p"], arrs[k + "v"] = m.indptr, m.vals
                    tm["axes"].append({"dims": list(m.dims), "key": k, "ncols": m.vals.shape[1]})
            for fi, (d, r) in enumerate(t.fixed):
                k = f"{side}{ti}f{fi}"
                arrs[k] = r
                tm["fixed"].append({"dims": list(d), "key": k, "ncols": r.shape[1]})
            meta[side].append(tm)
    arrs["meta"] = np.frombuffer(json.dumps(meta).encode(), np.uint8)
    _NP_SAVEZ_COMPRESSED(path, **arrs)


def load_prov(path) -> P.Prov:
    with _NP_LOAD(path, allow_pickle=False) as z:
        meta = json.loads(bytes(z["meta"]).decode())
        sides = {}
        for side in ("lo", "hi"):
            terms = []
            for tm in meta[side]:
                axes = []
                for a in tm["axes"]:
                    if a is None:
                        axes.append(None)
                    else:
                        v = z[a["key"] + "v"]
                        axes.append(P.AxisMap(tuple(a["dims"]), z[a["key"] + "p"], v))
                fixed = tuple((tuple(f["dims"]), z[f["key"]]) for f in tm["fixed"])
                terms.append(P.Term(tuple(axes), fixed))
            sides[side] = tuple(terms)
    return P.Prov(sides["lo"], sides["hi"], frozenset(meta["flags"]))


# --------------------------------------------------------------- ledger

def _probe(r: np.ndarray, k: int = 8) -> list:
    flat = np.asarray(r).reshape(-1)
    if flat.dtype.kind != "f" or not flat.size:
        return []
    idx = np.unique(np.linspace(0, flat.size - 1, num=min(64, flat.size)).astype(np.int64))
    out = []
    for i in idx:
        v = flat[i]
        if not np.isnan(v):
            out.append([int(i), int(np.float32(v).view(np.uint32))])
            if len(out) >= k:
                break
    return out


def _norm_key(key, shape):
    """Outer-indexing key (one entry per axis), as the data libraries apply it:
    a list of (kind, value) with kind "int" (value int), "slice" (value
    [start, stop, step] after slice.indices) or "list" (value int array)."""
    if not isinstance(key, tuple):
        key = (key,)
    if sum(1 for k in key if k is Ellipsis) > 1:
        raise IndexError("an index can only have a single ellipsis")
    n_real = len([k for k in key if k is not Ellipsis and k is not None])
    out = []
    for k in key:
        if k is Ellipsis:
            for _ in range(len(shape) - n_real):
                out.append(("slice", [0, shape[len(out)], 1]))
            continue
        if k is None:
            continue
        ax = len(out)
        if isinstance(k, slice):
            out.append(("slice", list(k.indices(shape[ax]))))
        elif isinstance(k, (int, np.integer)) and not isinstance(k, (bool, np.bool_)):
            out.append(("int", int(k) % shape[ax]))
        else:
            a = np.asarray(_unwrap(k))
            if a.dtype == bool:
                a = np.nonzero(a)[0]
            out.append(("list", a.astype(np.int64).reshape(-1) % shape[ax]))
    while len(out) < len(shape):
        out.append(("slice", [0, shape[len(out)], 1]))
    return out


def _key_json(nkey):
    return [[kind, v if kind != "list" else _rle(v)] for kind, v in nkey]


def _outer_prov(fid: int, shape, nkey) -> tuple[P.Prov, tuple]:
    """Provenance of an outer-indexed read of a (t, j, i) variable of file `fid`."""
    if len(shape) != 3:
        raise P._Unsupported
    p = P.source(shape, [("t",), ("j",), ("i",)], [np.arange(n) for n in shape],
                 fixed=[(("f",), [[fid]])])
    cur = tuple(shape)
    ax = 0
    for kind, v in nkey:
        if kind == "int":
            p, cur = P.getitem(p, cur, (slice(None),) * ax + (v,))
        else:
            idx = np.arange(*v) if kind == "slice" else np.asarray(v, np.int64)
            p, cur = P.getitem(p, cur, (slice(None),) * ax + (idx,))
            ax += 1
    return p, cur


@_timed
def ledger(lib: str, ident: str, var_shape, key, result, extra=None):
    """Record one materialisation of the SST variable and return the result
    carrying its provenance (the same values, the same type for masked arrays)."""
    st = _STATE
    if st is None:
        return result
    try:
        var_shape = tuple(int(n) for n in var_shape)
        nkey = _norm_key(key, var_shape)
        fid = st.file_id(ident)
        data = result.data if isinstance(result, np.ma.MaskedArray) else result
        arr = np.asarray(data)
        rec = {"t": time.time(), "lib": lib, "fid": fid, "var_shape": list(var_shape),
               "key": _key_json(nkey), "shape": list(np.shape(result)), "probes": _probe(arr),
               "crc": zlib.crc32(np.ascontiguousarray(arr).view(np.uint8)) if arr.ndim else None}
        if extra:
            rec.update(extra)
        st._write("ledger", rec)
        if not isinstance(result, np.ndarray):
            st.count("scalar_read")
            _escape_prov(_outer_prov(fid, var_shape, nkey)[0], "scalar_read")
            return result
        p, shp = _outer_prov(fid, var_shape, nkey)
        if shp != np.shape(result):
            st.count("ledger_shape_mismatch")
            p = P.Prov.none()
        if isinstance(result, np.ma.MaskedArray):
            d = _wrap(np.ndarray.view(np.asarray(result.data), np.ndarray), p)
            m = result.mask
            if isinstance(m, np.ndarray) and m.shape == result.shape:
                m = _wrap(np.ndarray.view(m, np.ndarray), p)
            return np.ma.MaskedArray(d, mask=m, fill_value=result.fill_value)
        return _wrap(result, p)
    except Exception:  # noqa: BLE001
        st.count("internal_error")
        return result
