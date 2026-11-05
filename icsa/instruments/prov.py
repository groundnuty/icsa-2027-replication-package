"""Positional provenance for the analysed-extent tracer (see DESIGN.md, tier 2).

A provenance `Prov` holds two term lists over one array's index space:
`lo` (units that certainly flow into the array's values) and `hi` (units that
may). A `Term` maps each array axis to an `AxisMap` or None, plus fixed
factors. An `AxisMap` gives, for every position along its axis, a set of
tuples over its dimensions (CSR: `indptr`, `vals`); an empty set means the
term does not cover that position. A fixed factor is a set of tuples shared
by every element. Within one term every dimension appears exactly once, and
the units of one element are the Cartesian product of its axis sets and the
fixed factors; the array's units are the union over terms.

The dimensions are opaque strings. The in-process tracer uses file id, time
index, lat index and lon index in file index space; `analyse` maps them to
global (day, lat, lon) offline.

Every operation here must keep `lo` an under-approximation and `hi` an
over-approximation of the true dependence of each element. When an operation
cannot be represented exactly, `lo` drops the term and `hi` collapses to a
product of per-dimension sets.
"""
from __future__ import annotations

import collections
import dataclasses
import hashlib
import itertools

import numpy as np

I64 = np.int64
MAX_TERMS = 128        # beyond this, lo is truncated (flagged) and hi collapsed; 512 cost K about 10% more tool time, same labels
MAX_ROWS = 20_000_000  # largest relation materialised in one axis map
MERGE_MOVE_MAX_ROWS = 200_000    # a fixed factor moved into an axis, to merge two terms: above this they stay two terms, exact
PROV_MAX_ROWS = 2_000_000        # the rows one side of one array's provenance may hold, shared arrays once: past it lo truncates, hi collapses
PROV_CHECK_TERMS = 32            # fewer terms than this are not worth counting on each operation
WORK_LIMIT = 5_700_000_000       # merge and product rows plus term work, one run (amendment 19(b)): calibrated on .23 at 9d83a49, 2 Nov
HOOK_WORK = 100                  # one hook, however little it does: a loop over millions of small arrays spends this
TERM_WORK = 200                  # one term tried for merging or mapped, in the same unit

MERGE_CALL_MAX_WORK = 30_000_000 # one merge past this leaves the rest of its terms apart, exact: 870 terms of a million rows, once

# Counted, not timed: a label must not depend on how busy the host was. [spent by this process, what it may spend].
_WORK = [0, float("inf")]
# By kind: rows merges and products produce, terms tried or mapped, hooks and arrays made. The budget is on the first two, unweighted
# (science's ruling on amendment 19(b)'s unit, #2, 18:11Z: term work bounds a run whose cost is mapping terms, with no merge rows);
# the sum of all three only paces the look at memory, and hooks are on record.
MERGE, TERMS, HOOKS = 0, 1, 2
_PARTS = [0, 0, 0]


def budgeted() -> int:
    """The work the budget counts: merge and product rows, and term work."""
    return _PARTS[MERGE] + _PARTS[TERMS]
_ON_OVER: list = [None]          # the tracer's: stops the tracking, once
STOPPED = [False]


def _work(n: int, part: int = MERGE) -> None:
    _PARTS[part] += n
    _WORK[0] += n
    if _WORK[0] > _WORK[1] and not STOPPED[0] and _ON_OVER[0] is not None:
        _ON_OVER[0]()


def _uniq(v: np.ndarray) -> np.ndarray:
    """Sorted distinct values of a 1-D int array: a table where the values span little, else a
    sort (per-cell loops ask for this tens of times per cell)."""
    n = len(v)
    if n < 2:
        return v
    low = int(v.min())
    span = int(v.max()) - low + 1
    if span <= 4 * n + 1024:
        seen = np.zeros(span, bool)
        seen[v - low] = True
        return np.flatnonzero(seen) + low
    x = np.sort(v)
    keep = np.empty(n, bool)
    keep[0] = True
    keep[1:] = x[1:] != x[:-1]
    return x[keep]


def _rows_unique(vals: np.ndarray) -> np.ndarray:
    if vals.shape[1] == 0:
        return np.empty((1 if len(vals) else 0, 0), I64)
    if len(vals) == 0:
        return vals
    if vals.shape[1] == 1:
        return _uniq(vals[:, 0])[:, None]
    # One int64 per row where it fits (lexicographic order kept): far faster than unique(axis=0).
    low = vals.min(axis=0)
    span = vals.max(axis=0) - low + 1
    if float(np.prod(span.astype(float))) < 2.0**62:
        weights = np.cumprod(np.concatenate([span[1:], [1]])[::-1])[::-1]
        codes = _uniq((vals - low) @ weights)
        out = np.empty((len(codes), vals.shape[1]), I64)
        for k, w in enumerate(weights):
            out[:, k] = codes // w + low[k]
            codes = codes % w
        return out
    return np.unique(vals, axis=0)


def _product(rels: list[np.ndarray]) -> np.ndarray:
    """Cartesian product of relations (each (m_i, k_i)) as one (prod m, sum k)."""
    out = np.empty((1, 0), I64)
    for r in rels:
        if len(out) * len(r) > MAX_ROWS:
            raise _TooBig
        a = np.repeat(out, len(r), axis=0)
        b = np.tile(r, (len(out), 1))
        out = np.hstack([a, b])
    return out


class _TooBig(Exception):
    pass


_FULL: dict = {}


def _same(a: np.ndarray, b: np.ndarray) -> bool:
    """Two arrays of integers hold the same: the question merging asks millions of times in a loop, most of them with
    a different answer early. numpy's array_equal costs microseconds more on each."""
    return a is b or (a.shape == b.shape and (a.size == 0 or (a[0] == b[0]).all() and bool((a == b).all())))


@dataclasses.dataclass(frozen=True, eq=False)
class AxisMap:
    dims: tuple[str, ...]
    indptr: np.ndarray   # int64 (n + 1,)
    vals: np.ndarray     # int64 (nnz, len(dims))

    @property
    def n(self) -> int:
        return len(self.indptr) - 1

    def counts(self) -> np.ndarray:
        c = self.__dict__.get("_counts")
        if c is None:
            c = np.diff(self.indptr)
            c.flags.writeable = False
            self.__dict__["_counts"] = c
        return c

    def covered(self) -> np.ndarray:
        c = self.__dict__.get("_covered")
        if c is None:
            c = self.counts() > 0
            c.flags.writeable = False
            self.__dict__["_covered"] = c
        return c

    def any_covered(self) -> bool:
        return int(self.indptr[-1]) > 0

    def single(self) -> bool:
        s = self.__dict__.get("_single")
        if s is None:
            s = self.__dict__["_single"] = bool(np.all(self.counts() <= 1))
        return s

    @classmethod
    def of(cls, dims, vals, covered=None) -> AxisMap:
        """One tuple per position: `vals` is (n,) for one dim or (n, k)."""
        vals = np.asarray(vals, I64)
        if vals.ndim == 1:
            vals = vals[:, None]
        n = len(vals)
        cov = np.ones(n, bool) if covered is None else np.asarray(covered, bool)
        ptr = np.zeros(n + 1, I64)
        np.cumsum(cov, out=ptr[1:])
        return cls(tuple(dims), ptr, vals[cov])

    @classmethod
    def presence(cls, n: int, covered) -> AxisMap:
        cov = np.zeros(n, bool)
        cov[np.asarray(covered)] = True
        ptr = np.zeros(n + 1, I64)
        np.cumsum(cov, out=ptr[1:])
        return cls((), ptr, np.empty((int(ptr[-1]), 0), I64))

    @classmethod
    def full(cls, n: int) -> AxisMap:
        """Every position covered, no dimensions. One object per length, so what is built from it
        is remembered across the calls of a per-cell loop."""
        m = _FULL.get(n)
        if m is None:
            if len(_FULL) >= 256:
                _FULL.clear()
            m = _FULL[n] = cls((), np.arange(n + 1, dtype=I64), np.empty((n, 0), I64))
        return m

    def take(self, idx) -> AxisMap:
        """The rows at `idx`. A contiguous run of positions shares this map's rows (a full run is
        this map itself), so repeated slices of one array cost nothing per element."""
        idx = np.asarray(idx, I64).reshape(-1)
        if len(idx) and self.n and idx[0] >= 0 and idx[-1] == idx[0] + len(idx) - 1 \
                and (len(idx) == 1 or bool(np.all(np.diff(idx) == 1))):
            return self._run(int(idx[0]), len(idx))
        c = self.counts()[idx]
        ptr = np.zeros(len(idx) + 1, I64)
        np.cumsum(c, out=ptr[1:])
        tot = int(ptr[-1])
        if tot > MAX_ROWS:
            raise _TooBig
        if tot:
            src = np.repeat(self.indptr[:-1][idx] - ptr[:-1], c) + np.arange(tot, dtype=I64)
            vals = self.vals[src]
        else:
            vals = np.empty((0, len(self.dims)), I64)
        return AxisMap(self.dims, ptr, vals)

    def _run(self, start: int, length: int) -> AxisMap:
        if start == 0 and length == self.n:
            return self
        cache = self.__dict__.setdefault("_runs", {})
        got = cache.get((start, length))
        if got is None:
            a, b = int(self.indptr[start]), int(self.indptr[start + length])
            got = AxisMap(self.dims, self.indptr[start:start + length + 1] - a, self.vals[a:b])
            if len(cache) < 16:             # slices of one array repeat: a few runs, kept with it
                cache[(start, length)] = got
        return got

    def union(self) -> np.ndarray:
        u = self.__dict__.get("_union")
        if u is None:
            u = _rows_unique(self.vals)
            u.flags.writeable = False
            self.__dict__["_union"] = u
        return u

    def place(self, positions, n: int) -> AxisMap:
        """This map's rows at `positions` (unique) of a length-n axis; elsewhere empty."""
        positions = np.asarray(positions, I64).reshape(-1)
        contiguous = len(positions) > 0 and (len(positions) == 1 or bool(np.all(np.diff(positions) == 1)))
        key = (int(positions[0]), len(positions), n) if contiguous else None
        cache = self.__dict__.setdefault("_places", {})
        if key is not None and key in cache:
            return cache[key]
        order = np.argsort(positions, kind="stable")
        moved = self.take(order)
        counts = np.zeros(n, I64)
        counts[positions[order]] = moved.counts()
        ptr = np.zeros(n + 1, I64)
        np.cumsum(counts, out=ptr[1:])
        out = AxisMap(self.dims, ptr, moved.vals)
        if key is not None and len(cache) < 16:
            cache[key] = out
        return out

    def blank(self, positions) -> AxisMap:
        """Same map with the rows at `positions` emptied."""
        keep = np.ones(self.n, bool)
        keep[np.asarray(positions, I64)] = False
        pos = np.nonzero(keep)[0]
        return self.take(pos).place(pos, self.n)

    def times(self, rels: list[tuple[tuple[str, ...], np.ndarray]]) -> AxisMap:
        """Every row multiplied by fixed factors (absorbing them into this axis). Remembered per
        factor object: a per-cell loop multiplies the same map by the same factors every time."""
        if not rels:
            return self
        cache = self.__dict__.setdefault("_times", {})
        key = tuple((d, id(r)) for d, r in rels)
        hit = cache.get(key)
        if hit is not None:
            return hit[1]
        out = self._times_new(rels)
        if len(cache) < 8:
            cache[key] = (rels, out)       # holding `rels` keeps their ids from being reused
        return out

    def _times_new(self, rels) -> AxisMap:
        dims = self.dims + tuple(d for ds, _ in rels for d in ds)
        prod = _product([r for _, r in rels])
        if len(self.vals) * len(prod) > MAX_ROWS:      # one step, one allocation: no later check could stop it
            raise _TooBig
        _work(len(self.vals) * len(prod))      # amendment 19(b): the rows a product produces
        c = self.counts()
        rows = np.repeat(np.arange(len(self.vals)), len(prod))
        tiled = np.tile(prod, (len(self.vals), 1))
        vals = np.hstack([self.vals[rows], tiled])
        ptr = np.zeros(self.n + 1, I64)
        np.cumsum(c * len(prod), out=ptr[1:])
        return _canon(AxisMap(dims, ptr, vals))

    def dim_sets(self) -> dict[str, np.ndarray]:
        """Each dimension's distinct values over all rows. Remembered with the map."""
        out = self.__dict__.get("_dim_sets")
        if out is None:
            out = self.__dict__["_dim_sets"] = {d: _uniq(self.vals[:, c]) for c, d in enumerate(self.dims)}
        return out

    def _digest(self) -> bytes:
        """Of the content, once per map: a loop over a long term list asks equal() of the same maps hundreds of thousands of
        times, and their first rows often agree. 128 bits: two different maps taken for one is not a case to plan for."""
        out = self.__dict__.get("_content")
        if out is None:
            h = hashlib.blake2b(self.indptr.tobytes(), digest_size=16)
            h.update(self.vals.tobytes())
            out = self.__dict__["_content"] = h.digest()
        return out

    def equal(self, other: AxisMap) -> bool:
        return self is other or (self.dims == other.dims and self.indptr.shape == other.indptr.shape
                                 and self.vals.shape == other.vals.shape and self._digest() == other._digest())


_ORDER: dict[str, int] = {}


def set_dim_order(dims) -> None:
    """Canonical order of dimension names (columns are kept in this order)."""
    _ORDER.clear()
    _ORDER.update({d: k for k, d in enumerate(dims)})


set_dim_order(("f", "t", "j", "i"))


def _canon(m: AxisMap) -> AxisMap:
    perm = sorted(range(len(m.dims)), key=lambda k: _ORDER.get(m.dims[k], 99))
    if perm == list(range(len(m.dims))):
        return m
    return AxisMap(tuple(m.dims[k] for k in perm), m.indptr, m.vals[:, perm])


@dataclasses.dataclass(frozen=True, eq=False)
class Term:
    axes: tuple                  # AxisMap | None per array axis
    fixed: tuple = ()            # ((dims, rel), ...)

    def empty(self) -> bool:
        return (any(len(r) == 0 for _, r in self.fixed)
                or any(m is not None and not m.any_covered() for m in self.axes))

    def dims(self) -> tuple[str, ...]:
        ds = [d for m in self.axes if m is not None for d in m.dims]
        ds += [d for dd, _ in self.fixed for d in dd]
        return tuple(sorted(ds, key=lambda d: _ORDER.get(d, 99)))

    def factors(self) -> list[tuple[tuple[str, ...], np.ndarray]]:
        """The term's unit set as a product of relations (empty list if empty)."""
        if self.empty():
            return []
        out = [(m.dims, m.union()) for m in self.axes if m is not None and m.dims]
        out += [(d, r) for d, r in self.fixed if d]
        return out

    def covered(self, shape) -> np.ndarray:
        """Bool array of `shape`: elements this term covers."""
        c = np.ones(shape, bool)
        for k, m in enumerate(self.axes):
            if m is not None:
                sh = [1] * len(shape)
                sh[k] = shape[k]
                c &= m.covered().reshape(sh)
        if any(len(r) == 0 for _, r in self.fixed):
            c[...] = False
        return c


def _clean(terms) -> tuple[Term, ...]:
    return tuple(t for t in terms if t is not None and not t.empty())


@dataclasses.dataclass(frozen=True, eq=False)
class Prov:
    lo: tuple[Term, ...]
    hi: tuple[Term, ...]
    flags: frozenset = frozenset()

    @classmethod
    def none(cls) -> Prov:
        return cls((), ())

    @classmethod
    def exact(cls, terms, flags=frozenset()) -> Prov:
        t = _clean(terms)
        return cls(t, t, frozenset(flags))

    def is_empty(self) -> bool:
        return not self.hi


def source(shape, axis_dims, axis_vals, fixed=()) -> Prov:
    """Provenance of freshly read data: axis k carries dims `axis_dims[k]`
    (a tuple, possibly empty) with one tuple per position `axis_vals[k]`."""
    axes = []
    for k, n in enumerate(shape):
        if axis_dims[k]:
            axes.append(_canon(AxisMap.of(axis_dims[k], axis_vals[k])))
        else:
            axes.append(None)
    fx = tuple((tuple(d), np.asarray(r, I64).reshape(-1, len(d))) for d, r in fixed)
    return Prov.exact([Term(tuple(axes), fx)])


# --------------------------------------------------------------- combinators

def collapse(terms, ndim: int) -> Term | None:
    """One term over-approximating all `terms`: per-dimension unions, all fixed."""
    sets: dict[str, list[np.ndarray]] = {}
    any_live = False
    for t in terms:
        if t.empty():
            continue
        any_live = True
        for m in t.axes:
            if m is not None and m.dims:
                for d, v in m.dim_sets().items():
                    sets.setdefault(d, []).append(v)
        for dims, rel in t.fixed:
            if len(dims) == 1:
                sets.setdefault(dims[0], []).append(rel[:, 0])
            else:
                for c, d in enumerate(dims):
                    sets.setdefault(d, []).append(rel[:, c])
    if not any_live:
        return None
    fixed = tuple(((d,), _union_sorted(v).reshape(-1, 1))
                  for d, v in sorted(sets.items(), key=lambda kv: _ORDER.get(kv[0], 99)))
    _work(sum(len(r) for _, r in fixed))       # amendment 19(b): a collapse is a merge, and produces these rows
    return Term((None,) * ndim, fixed)


def _union_sorted(parts: list[np.ndarray]) -> np.ndarray:
    first = parts[0]
    if all(x is first for x in parts):
        return _uniq(first)
    return _uniq(np.concatenate(parts))


def _within_rows(terms) -> int:
    """How many of these terms fit in PROV_MAX_ROWS, each array counted once."""
    seen: set[int] = set()
    n = 0
    for at, t in enumerate(terms):
        for m in t.axes:
            if m is not None and id(m.vals) not in seen:
                seen.add(id(m.vals))
                n += len(m.vals)
        for _, r in t.fixed:
            if id(r) not in seen:
                seen.add(id(r))
                n += len(r)
        if n > PROV_MAX_ROWS:
            return at
    return len(terms)


def _cap(p: Prov, ndim: int) -> Prov:
    lo, hi, flags = p.lo, p.hi, set(p.flags)
    if len(lo) > MAX_TERMS:
        lo = lo[:MAX_TERMS]
        flags.add("lo_truncated")
    if len(lo) >= PROV_CHECK_TERMS:
        keep = _within_rows(lo)
        if keep < len(lo):
            lo = lo[:keep]
            flags.add("lo_truncated")
    if len(hi) > MAX_TERMS or (len(hi) >= PROV_CHECK_TERMS and _within_rows(hi) < len(hi)):
        c = collapse(hi, ndim)
        hi = (c,) if c is not None else ()
    return Prov(lo, hi, frozenset(flags))


def _map_terms(p: Prov, fn, ndim_out: int, *, lo_ok=True) -> Prov:
    """Apply a per-term transform to lo and hi; on failure lo drops, hi collapses."""
    flags = set(p.flags)
    done: dict[int, Term] = {}         # a term in both lists gets one result, which stays shared

    def once(t: Term):
        r = done.get(id(t))
        if r is None:
            _work(TERM_WORK, TERMS)
            r = done[id(t)] = fn(t)
        return r
    lo = []
    if lo_ok:
        for t in p.lo:
            try:
                r = once(t)
                lo.extend(r) if isinstance(r, list) else lo.append(r)
            except (_TooBig, _Unsupported):
                flags.add("lo_dropped")
    elif p.lo:
        flags.add("lo_dropped")
    hi = []
    failed = []
    for t in p.hi:
        try:
            r = once(t)
            hi.extend(r) if isinstance(r, list) else hi.append(r)
        except (_TooBig, _Unsupported):
            failed.append(t)
    if failed:
        c = collapse(failed, ndim_out)
        if c is not None:
            hi.append(c)
    return _cap(Prov(_clean(lo), _clean(hi), frozenset(flags)), ndim_out)


class _Unsupported(Exception):
    pass


def union(provs, ndim: int) -> Prov:
    los, his, flags = [], [], set()
    for p in provs:
        los.append(p.lo)
        his.append(p.hi)
        flags |= p.flags
    return _cap(Prov(_merge_parts(los), _merge_parts(his), frozenset(flags)), ndim)


def file_ids(p: Prov) -> set[int]:
    """The file numbers a provenance names (the column "f" of its factors)."""
    out: set[int] = set()
    for t in (*p.lo, *p.hi):
        for m in t.axes:
            if m is not None and "f" in m.dims:
                out.update(int(v) for v in np.unique(m.vals[:, m.dims.index("f")]))
        for dims, rel in t.fixed:
            if "f" in dims:
                out.update(int(v) for v in np.unique(np.asarray(rel)[:, dims.index("f")]))
    return out


def remap_files(p: Prov, mapping: dict[int, int]) -> Prov:
    """The same provenance with its file numbers replaced: a process's numbers mean nothing in another process."""
    keys = np.array(sorted(mapping), I64)
    vals = np.array([mapping[int(k)] for k in keys], I64)

    def col(r, c):
        r = np.array(r, I64, copy=True)
        r[:, c] = vals[np.searchsorted(keys, r[:, c])]
        return r

    def term(t: Term) -> Term:
        axes = tuple(m if m is None or "f" not in m.dims else AxisMap(m.dims, m.indptr, col(m.vals, m.dims.index("f")))
                     for m in t.axes)
        fixed = tuple((d, _rows_unique(col(r, d.index("f"))) if "f" in d else r) for d, r in t.fixed)
        return Term(axes, fixed)
    return Prov(tuple(term(t) for t in p.lo), tuple(term(t) for t in p.hi), p.flags)


MERGE_ONTO = 64


def _merge_parts(parts) -> tuple[Term, ...]:
    """merge() of the parts. An accumulator in a loop is one long part, merged when it was made, and a few new terms:
    only those are merged, onto its end, or each step would cost the whole list again (a Python loop over cells).
    Which terms are kept past the cap does not matter for the bounds: the lower bound is only smaller, and flagged."""
    big = max(parts, key=len, default=())
    if len(big) < MERGE_ONTO:
        return merge([t for part in parts for t in part])
    return merge([t for part in parts if part is not big for t in part], onto=big)


def hi_only(p: Prov, ndim: int) -> Prov:
    """An unmodelled operation of the inputs: lo nothing, hi everything, as fixed."""
    c = collapse(p.hi, ndim)
    flags = set(p.flags)
    if p.lo:
        flags.add("unmodelled")
    return Prov((), (c,) if c is not None else (), frozenset(flags))


# --------------------------------------------------------------- broadcasting

def broadcast(p: Prov, shape, out_shape) -> Prov:
    shape, out_shape = tuple(shape), tuple(out_shape)
    if shape == out_shape:
        return p
    pad = len(out_shape) - len(shape)
    if pad < 0:
        raise ValueError("cannot broadcast to fewer dims")

    def fn(t: Term) -> Term:
        axes = [None] * pad
        for k, m in enumerate(t.axes):
            n_out = out_shape[pad + k]
            if m is not None and m.n == 1 and n_out != 1:
                m = m.take(np.zeros(n_out, I64))
            axes.append(m)
        return Term(tuple(axes), t.fixed)
    return _map_terms(p, fn, len(out_shape))


# --------------------------------------------------------------- indexing

@dataclasses.dataclass
class _Key:
    """A numpy index expression resolved against a shape."""
    out_axes: list          # ('src', k, idx) | ('new',) | ('adv',)
    drops: list             # (k, i): source axis k fixed at index i
    adv_axes: list          # source axes taken by the advanced index
    adv_idx: list           # flat int arrays (length nB), one per adv axis
    out_shape: tuple


def _is_int(x) -> bool:
    return isinstance(x, (int, np.integer)) and not isinstance(x, (bool, np.bool_))


def resolve_key(key, shape) -> _Key:
    """Resolve `key` the way numpy does; raises _Unsupported for what is not modelled."""
    shape = tuple(shape)
    if not isinstance(key, tuple):
        key = (key,)
    # Expand bools into nonzero arrays, find the ellipsis.
    items = []
    for x in key:
        if isinstance(x, list):
            x = np.asarray(x)
            if x.dtype == object:
                raise _Unsupported
        if isinstance(x, np.ndarray) and x.dtype == bool:
            if x.ndim == 0:
                raise _Unsupported
            items.append(("bool", x))
        elif isinstance(x, np.ndarray) and x.dtype.kind in "iu":
            items.append(("arr", x))
        elif isinstance(x, np.ndarray):
            raise _Unsupported
        elif x is None:
            items.append(("new", None))
        elif x is Ellipsis:
            items.append(("ell", None))
        elif isinstance(x, slice):
            items.append(("slice", x))
        elif _is_int(x):
            items.append(("int", int(x)))
        else:
            raise _Unsupported
    used = sum(x[1].ndim if x[0] == "bool" else (0 if x[0] in ("new", "ell") else 1) for x in items)
    if used > len(shape):
        raise IndexError("too many indices")
    nell = sum(1 for x in items if x[0] == "ell")
    if nell > 1:
        raise IndexError("an index can only have a single ellipsis")
    full = []
    for x in items:
        if x[0] == "ell":
            width = len(shape) - used
            full += [("slice", slice(None))] * width if width else [("gap", None)]
        else:
            full.append(x)
    if nell == 0:
        full += [("slice", slice(None))] * (len(shape) - used)
    has_arr = any(x[0] in ("arr", "bool") for x in full)
    # Walk source axes.
    k = 0
    out_axes, drops, adv_axes, adv_raw, adv_pos = [], [], [], [], []
    gaps = 0   # zero-width ellipses: they separate advanced indices but add no axis
    for x in full:
        kind, v = x
        if kind == "gap":
            gaps += 1
            continue
        if kind == "new":
            out_axes.append(("new",))
        elif kind == "slice":
            out_axes.append(("src", k, np.arange(*v.indices(shape[k]), dtype=I64)))
            k += 1
        elif kind == "int":
            i = v + shape[k] if v < 0 else v
            if not 0 <= i < shape[k]:
                raise IndexError(f"index {v} out of bounds for axis {k}")
            if has_arr:
                adv_pos.append(len(out_axes) + gaps)
                out_axes.append(("adv",))
                adv_axes.append(k)
                adv_raw.append(np.asarray(i, I64))
            else:
                drops.append((k, i))
            k += 1
        elif kind == "arr":
            a = v.astype(I64)
            a = np.where(a < 0, a + shape[k], a)
            if a.size and (a.min() < 0 or a.max() >= shape[k]):
                raise IndexError(f"index out of bounds for axis {k}")
            adv_pos.append(len(out_axes) + gaps)
            out_axes.append(("adv",))
            adv_axes.append(k)
            adv_raw.append(a)
            k += 1
        elif kind == "bool":
            if v.shape != shape[k:k + v.ndim]:
                raise IndexError("boolean index shape mismatch")
            nz = np.nonzero(v)
            for c in range(v.ndim):
                adv_pos.append(len(out_axes) + gaps)
                out_axes.append(("adv",))
                adv_axes.append(k + c)
                adv_raw.append(nz[c].astype(I64))
            k += v.ndim
    adv_idx = []
    if adv_axes:
        try:
            b = np.broadcast_arrays(*adv_raw)
        except ValueError as e:
            raise IndexError(f"shape mismatch: indexing arrays could not be broadcast together ({e})") from None
        if b[0].ndim > 1:
            raise _Unsupported
        if b[0].ndim == 0:
            # Only scalar (0-d) advanced indices: they act as integers and drop their axes.
            for k, x in zip(adv_axes, b):
                n, i = shape[k], int(x)
                if not -n <= i < n:
                    raise IndexError(f"index {i} is out of bounds for axis {k} with size {n}")
                drops.append((k, i + n if i < 0 else i))
            out_axes = [a for a in out_axes if a[0] != "adv"]
            shp = [1 if a[0] == "new" else len(a[2]) for a in out_axes]
            return _Key(out_axes, sorted(drops), [], [], tuple(shp))
        nb = b[0].size
        adv_idx = [np.asarray(x, I64).reshape(-1) if x.ndim else np.full(nb, int(x), I64) for x in b]
        # numpy: the broadcast advanced dims replace the adv block if contiguous, else go first.
        contiguous = adv_pos == list(range(adv_pos[0], adv_pos[0] + len(adv_pos)))
        first = sum(1 for a in out_axes[:out_axes.index(("adv",))] if a[0] != "adv") if contiguous else 0
        rest = [a for a in out_axes if a[0] != "adv"]
        nd = b[0].ndim
        block = [("adv",)] * nd
        out_axes = rest[:first] + block + rest[first:] if contiguous else block + rest
    shp = []
    for a in out_axes:
        if a[0] == "new":
            shp.append(1)
        elif a[0] == "src":
            shp.append(len(a[2]))
        else:
            shp.append(len(adv_idx[0]))
    return _Key(out_axes, drops, adv_axes, adv_idx, tuple(shp))


def _getitem_term(t: Term, rk: _Key) -> Term:
    fixed = list(t.fixed)
    for k, i in rk.drops:
        m = t.axes[k]
        if m is not None:
            row = m.take([i])
            if not row.covered()[0]:
                return Term((None,) * len(rk.out_axes), (((), np.empty((0, 0), I64)),))
            if m.dims:
                fixed.append((m.dims, row.vals))
    adv_map = None
    if rk.adv_axes:
        nb = len(rk.adv_idx[0])
        maps = [(t.axes[k], idx) for k, idx in zip(rk.adv_axes, rk.adv_idx)]
        live = [(m, idx) for m, idx in maps if m is not None]
        if live:
            cov = np.ones(nb, bool)
            for m, idx in live:
                cov &= m.covered()[idx]
            if len(live) == 1:
                m, idx = live[0]
                adv_map = m.take(idx)
            elif any(not m.single() for m, _ in live):
                raise _Unsupported
            else:
                dims = tuple(d for m, _ in live for d in m.dims)
                cols = [m.vals[m.indptr[:-1][idx[cov]]] for m, idx in live]
                vals = np.hstack(cols) if cols else np.empty((int(cov.sum()), 0), I64)
                ptr = np.zeros(nb + 1, I64)
                np.cumsum(cov, out=ptr[1:])
                adv_map = _canon(AxisMap(dims, ptr, vals))
    axes = []
    for a in rk.out_axes:
        if a[0] == "new":
            axes.append(None)
        elif a[0] == "src":
            m = t.axes[a[1]]
            axes.append(None if m is None else m.take(a[2]))
        else:
            axes.append(adv_map)
    return Term(tuple(axes), tuple(fixed))


def getitem(p: Prov, shape, key) -> tuple[Prov, tuple]:
    """Provenance of `x[key]` for x of `shape`; returns (prov, result shape)."""
    rk = resolve_key(key, shape)
    return _map_terms(p, lambda t: _getitem_term(t, rk), len(rk.out_shape)), rk.out_shape


def key_dependence(index_prov: Prov, index_shape, rk_shape, place_axes, ndim_out) -> Prov:
    """Provenance a tracked index array lends to the result of an indexing
    (selection dependence): the index's terms placed on the result axes that
    the advanced index produced (`place_axes`), None elsewhere."""
    def fn(t: Term) -> Term:
        if len(t.axes) != len(place_axes):
            raise _Unsupported
        axes = [None] * ndim_out
        for a, k in zip(t.axes, place_axes):
            axes[k] = a
        return Term(tuple(axes), t.fixed)
    return _map_terms(index_prov, fn, ndim_out)


# --------------------------------------------------------------- reductions

def reduce(p: Prov, shape, axis, keepdims=False) -> Prov:
    nd = len(shape)
    if axis is None:
        axes = set(range(nd))
    else:
        axes = {a % nd for a in (axis if isinstance(axis, (tuple, list)) else (axis,))}

    def fn(t: Term) -> Term:
        fixed = list(t.fixed)
        out = []
        for k, m in enumerate(t.axes):
            if k in axes:
                if m is not None:
                    if not m.covered().any():
                        return Term((None,) * (nd if keepdims else nd - len(axes)),
                                    (((), np.empty((0, 0), I64)),))
                    if m.dims:
                        fixed.append((m.dims, m.union()))
                if keepdims:
                    out.append(None)
            else:
                out.append(m)
        return Term(tuple(out), tuple(fixed))
    return _map_terms(p, fn, nd if keepdims else nd - len(axes))


def mix_axis(p: Prov, shape, axis) -> Prov:
    """Every element along `axis` depends on every element along it (sort, cumsum
    upper bound): the axis becomes unaligned, its sets a fixed factor."""
    nd = len(shape)
    axis %= nd
    r = reduce(p, shape, axis, keepdims=True)
    return broadcast(r, tuple(1 if k == axis else n for k, n in enumerate(shape)), shape)


def shifted(p: Prov, shape, axis, offsets, n_out) -> Prov:
    """Element i along `axis` depends on elements i + o for every o in `offsets`
    (diff, sliding windows): one term per offset, exact."""
    nd = len(shape)
    axis %= nd
    parts = []
    for o in offsets:
        idx = np.arange(n_out, dtype=I64) + o
        key = tuple(idx if k == axis else slice(None) for k in range(nd))
        q, _ = getitem(p, shape, key)
        parts.append(q)
    return union(parts, nd)


# --------------------------------------------------------------- shape ops

def transpose(p: Prov, perm) -> Prov:
    perm = list(perm)
    return _map_terms(p, lambda t: Term(tuple(t.axes[k] for k in perm), t.fixed), len(perm))


def _reshape_groups(a, b):
    """Groups of consecutive axes (ga, gb) with equal products; size-1 axes form own groups."""
    i = j = 0
    groups = []
    while i < len(a) or j < len(b):
        if i < len(a) and a[i] == 1 and (j >= len(b) or b[j] != 1):
            groups.append(([i], []))
            i += 1
            continue
        if j < len(b) and b[j] == 1 and (i >= len(a) or a[i] != 1):
            groups.append(([], [j]))
            j += 1
            continue
        if i >= len(a) or j >= len(b):
            raise _Unsupported
        ga, gb = [i], [j]
        pa, pb = a[i], b[j]
        i += 1
        j += 1
        while pa != pb:
            if pa < pb:
                pa *= a[i]
                ga.append(i)
                i += 1
            else:
                pb *= b[j]
                gb.append(j)
                j += 1
        groups.append((ga, gb))
    return groups


def reshape(p: Prov, shape, new_shape) -> Prov:
    shape, new_shape = tuple(shape), tuple(new_shape)
    if shape == new_shape:
        return p
    groups = _reshape_groups(shape, new_shape)

    def fn(t: Term):
        axes = [None] * len(new_shape)
        splits = []                         # (output axes, the map being split, the sub-shape)
        for ga, gb in groups:
            maps = [t.axes[k] for k in ga]
            if not gb:                      # a size-1 axis removed
                m = maps[0]
                if m is not None and not m.covered().all():
                    raise _Unsupported
                if m is not None and m.dims:
                    raise _Unsupported
                continue
            if not ga:                      # a size-1 axis added
                continue
            if len(gb) == 1:                # merge ga into one axis (C order)
                live = [(c, m) for c, m in enumerate(maps) if m is not None]
                if not live:
                    continue
                sub = [shape[k] for k in ga]
                grid = np.indices(sub).reshape(len(sub), -1)
                if len(live) == 1:
                    c, m = live[0]
                    axes[gb[0]] = m.take(grid[c])
                else:
                    if any(not m.single() for _, m in live):
                        raise _Unsupported
                    cov = np.ones(grid.shape[1], bool)
                    for c, m in live:
                        cov &= m.covered()[grid[c]]
                    cols = [m.vals[m.indptr[:-1][grid[c][cov]]] for c, m in live]
                    ptr = np.zeros(grid.shape[1] + 1, I64)
                    np.cumsum(cov, out=ptr[1:])
                    axes[gb[0]] = _canon(AxisMap(tuple(d for _, m in live for d in m.dims), ptr,
                                                 np.hstack(cols)))
            elif len(ga) == 1:              # split one axis
                if maps[0] is not None:
                    splits.append((gb, maps[0], tuple(new_shape[b] for b in gb)))
            else:
                if any(m is not None for m in maps):
                    raise _Unsupported
        if not splits:
            return Term(tuple(axes), t.fixed)
        out = [(axes, ())]
        for gb, m, sub in splits:
            nxt = []
            for ax, extra in out:
                for parts, fx in _split_map(m, sub):
                    a = list(ax)
                    for b, mm in zip(gb, parts):
                        a[b] = mm
                    nxt.append((a, extra + fx))
            out = nxt
            if len(out) > SPLIT_TERMS:
                raise _Unsupported
        return [Term(tuple(a), t.fixed + fx) for a, fx in out]
    return _map_terms(p, fn, len(new_shape))


SPLIT_TERMS = 256       # an axis split into more terms than this gives up its lower bound (sound)


def _split_map(m: AxisMap, sub: tuple) -> list[tuple[list, tuple]]:
    """One axis of length prod(sub) (C order) as len(sub) axes: a list of (maps, fixed factors), one per output
    term, whose union gives every position exactly m's rows there."""
    if len(sub) == 1:
        return [([m], ())]
    if len(sub) > 2:
        out = []
        for (ma, mb), fx in _split_map(m, (sub[0], int(np.prod(sub[1:])))):
            if mb is None:
                out.append(([ma] + [None] * (len(sub) - 1), fx))
                continue
            for rest, fx2 in _split_map(mb, sub[1:]):
                out.append(([ma] + rest, fx + fx2))
        return out
    H, W = sub
    cov = m.covered().reshape(H, W)
    rows = np.flatnonzero(cov.any(axis=1))
    if not len(rows):
        return []
    # rows that share a pattern of covered columns form one term
    groups: dict[bytes, list[int]] = {}
    for j in rows:
        groups.setdefault(np.packbits(cov[j]).tobytes(), []).append(int(j))
    if m.dims and m.single():
        sep = _separable(m, cov, H, W)
        if sep is not None:
            jd, jv, idims, iv = sep
            out = []
            for js in groups.values():
                cols = np.flatnonzero(cov[js[0]])
                aj = _canon(AxisMap.of(jd, jv[js], None)).place(js, H) if jd else AxisMap.presence(H, js)
                ai = _canon(AxisMap.of(idims, iv[cols], None)).place(cols, W) if idims else AxisMap.presence(W, cols)
                out.append(([aj, ai], ()))
            return out
    if not m.dims:
        return [([AxisMap.presence(H, js), AxisMap.presence(W, np.flatnonzero(cov[js[0]]))], ()) for js in groups.values()]
    # not separable: one term per row, the row's positions keeping their own rows
    if len(rows) > SPLIT_TERMS:
        raise _Unsupported
    return [([AxisMap.presence(H, [j]), m.take(np.arange(j * W, (j + 1) * W))], ()) for j in rows]


def _separable(m: AxisMap, cov, H, W):
    """For a map with one row per covered position: whether each dimension's value depends on the row alone or
    on the column alone, over the covered positions. Returns (row dims, (H, k) values, column dims, (W, k')
    values), or None."""
    pos = np.flatnonzero(cov.reshape(-1))
    vals = m.vals                                   # one row per covered position, in position order
    pj, pi = pos // W, pos % W
    jd, idims, jcols, icols = [], [], [], []
    for c, d in enumerate(m.dims):
        v = vals[:, c]
        by_j = np.zeros(H, I64)
        by_j[pj[::-1]] = v[::-1]                    # the first covered position's value in each row
        if np.array_equal(by_j[pj], v):
            jd.append(d)
            jcols.append(by_j)
            continue
        by_i = np.zeros(W, I64)
        by_i[pi[::-1]] = v[::-1]
        if np.array_equal(by_i[pi], v):
            idims.append(d)
            icols.append(by_i)
            continue
        return None
    jv = np.column_stack(jcols) if jcols else np.empty((H, 0), I64)
    iv = np.column_stack(icols) if icols else np.empty((W, 0), I64)
    return tuple(jd), jv, tuple(idims), iv


def concatenate(parts, shapes, axis) -> Prov:
    """parts[i] is the provenance of an operand of shape shapes[i]."""
    nd = len(shapes[0])
    axis %= nd
    n = sum(s[axis] for s in shapes)
    out_lo, out_hi, flags = [], [], set()
    off = 0
    for p, s in zip(parts, shapes):
        pos = np.arange(off, off + s[axis], dtype=I64)
        off += s[axis]
        q = _map_terms(p, lambda t, pos=pos: _place_on_axis(t, axis, pos, n), nd)
        out_lo += q.lo
        out_hi += q.hi
        flags |= q.flags
    return _cap(Prov(merge(out_lo), merge(out_hi), frozenset(flags)), nd)


def _place_on_axis(t: Term, axis: int, pos, n: int) -> Term:
    m = t.axes[axis]
    if m is None:
        m = AxisMap.full(len(pos))
    # Operands that differ in a fixed factor (one file each) still merge into one term: merge
    # moves what differs into this axis. Absorbing it here would rebuild the map for every call.
    axes = list(t.axes)
    axes[axis] = m.place(pos, n)
    return Term(tuple(axes), t.fixed)


# --------------------------------------------------------------- setitem

def _element_index(key, shape) -> tuple | None:
    """`key` as one element's index (non-negative ints, one per axis), or None if it is anything else."""
    items = key if isinstance(key, tuple) else (key,)
    if len(items) != len(shape) or not shape:
        return None
    out = []
    for x, n in zip(items, shape):
        if not _is_int(x):
            return None
        i = int(x)
        i = i + n if i < 0 else i
        if not 0 <= i < n:
            return None
        out.append(i)
    return tuple(out)


def _has(m: AxisMap, i: int) -> bool:
    ptr = m.indptr
    return ptr[i + 1] != ptr[i]


def _covers(t: Term, idx) -> bool:
    for _, r in t.fixed:
        if len(r) == 0:
            return False
    for m, i in zip(t.axes, idx):
        if m is not None and not _has(m, i):
            return False
    return True


_PRESENCE: dict = {}


def _presence_at(n: int, i: int) -> AxisMap:
    """One covered position, no dimensions; one object per (n, i), so that terms built from it compare by identity."""
    m = _PRESENCE.get((n, i))
    if m is None:
        if len(_PRESENCE) >= 4096:
            _PRESENCE.clear()
        m = _PRESENCE[(n, i)] = AxisMap.presence(n, [i])
    return m


def _set_rows(m: AxisMap, i: int, rows: np.ndarray) -> AxisMap:
    """m with `rows` at position i, which m does not cover."""
    a = int(m.indptr[i])
    ptr = m.indptr.copy()
    ptr[i + 1:] += len(rows)
    return AxisMap(m.dims, ptr, np.concatenate([m.vals[:a], rows, m.vals[a:]]))


def _element_terms(value_terms, shape, idx) -> list[Term]:
    """The terms of a 0-d value written at one element: every axis covered at its index only, the value's
    single-row factors on the last axis (one row there), its other factors fixed. Each element's units are
    the value's units, as `_place_region` gives them."""
    nd = len(shape)
    out = []
    for vt in value_terms:
        single = [(d, r) for d, r in vt.fixed if d and len(r) == 1]
        multi = tuple((d, r) for d, r in vt.fixed if not (d and len(r) == 1))
        axes = [_presence_at(shape[k], idx[k]) for k in range(nd - 1)]
        if single:
            dims = tuple(x for d, _ in single for x in d)
            row = np.hstack([r for _, r in single]).astype(I64).reshape(1, -1)
            ptr = np.zeros(shape[-1] + 1, I64)
            ptr[idx[-1] + 1:] = 1
            last = _canon(AxisMap(dims, ptr, row))
        else:
            last = _presence_at(shape[-1], idx[-1])
        axes.append(last)
        out.append(Term(tuple(axes), multi))
    return out


def _absorb_element(terms: list, e: Term, idx) -> None:
    """Add element term e to `terms`, extending a term that differs from it only in the last axis (which does
    not cover the element) if one of the last few does; exact, as merge's disjoint union."""
    nd = len(idx)
    for n in range(len(terms) - 1, max(-1, len(terms) - 9), -1):
        t = terms[n]
        if len(t.axes) != nd:
            continue
        lt, le = t.axes[-1], e.axes[-1]
        if lt is None or lt.dims != le.dims or _has(lt, idx[-1]):
            continue
        if any(not (a is b or (a is not None and b is not None and a.equal(b))) for a, b in zip(t.axes[:-1], e.axes[:-1])):
            continue
        if not _fixed_equal(t.fixed, e.fixed):
            continue
        a, b = int(le.indptr[idx[-1]]), int(le.indptr[idx[-1] + 1])
        terms[n] = Term(t.axes[:-1] + (_set_rows(lt, idx[-1], le.vals[a:b]),), t.fixed)
        return
    terms.append(e)


def _set_element(target: Prov, shape, idx, value: Prov | None) -> Prov | None:
    """`x[i, j, ...] = v` for a 0-d v at an element no term of x covers (a loop filling an array): the old terms
    stay as they are, and the value's terms are added there. None if this does not apply."""
    if any(_covers(t, idx) for t in target.lo) or any(_covers(t, idx) for t in target.hi):
        return None
    if value is None or value.is_empty():
        return target
    if any(len(t.axes) for t in value.lo) or any(len(t.axes) for t in value.hi):
        return None
    lo, hi = list(target.lo), list(target.hi)
    for side, vterms in ((lo, value.lo), (hi, value.hi)):
        for e in _element_terms(vterms, shape, idx):
            _absorb_element(side, e, idx)
    return _cap(Prov(tuple(lo), tuple(hi), target.flags | value.flags), len(shape))


def _flat_bool_key(key, shape):
    """`key` with one boolean array over several axes and full slices elsewhere: (first axis, number of axes, the
    key with that array as flat positions). None for anything else."""
    items = key if isinstance(key, tuple) else (key,)
    bools = [n for n, x in enumerate(items) if isinstance(x, np.ndarray) and x.dtype == bool and x.ndim >= 2]
    if len(bools) != 1:
        return None
    if any(x is Ellipsis or x is None for x in items):
        return None
    b = bools[0]
    others = [x for n, x in enumerate(items) if n != b]
    if any(not (isinstance(x, slice) and x == slice(None)) for x in others):
        return None
    m = items[b].ndim
    if b + m + (len(items) - b - 1) > len(shape) or items[b].shape != tuple(shape[b:b + m]):
        return None
    flat = tuple(items[:b]) + (np.flatnonzero(items[b]),) + tuple(items[b + 1:])
    return b, m, flat


def setitem(target: Prov, shape, key, value: Prov | None, value_shape, key_prov: Prov | None = None) -> Prov:
    """Provenance of x after `x[key] = value` (x of `shape`)."""
    shape = tuple(shape)
    nd = len(shape)
    fk = _flat_bool_key(key, shape)
    if fk is not None:
        # x[:, mask2d] = v: the masked axes as one, the positions written there, the axes split back (exact)
        b, m, flat_key = fk
        flat_shape = shape[:b] + (int(np.prod(shape[b:b + m])),) + shape[b + m:]
        q = setitem(reshape(target, shape, flat_shape), flat_shape, flat_key, value, value_shape)
        q = reshape(q, flat_shape, shape)
        if key_prov is not None and not key_prov.is_empty():
            q = _cap(Prov(merge(_clean(list(q.lo) + list(key_prov.lo))), merge(_clean(list(q.hi) + list(key_prov.hi))),
                          q.flags | key_prov.flags), nd)
        return q
    if key_prov is None and tuple(value_shape) == ():
        idx = _element_index(key, shape)
        if idx is not None:
            r = _set_element(target, shape, idx, value)
            if r is not None:
                return r
    rk = resolve_key(key, shape)
    flags = set(target.flags)
    # The region written, as per-source-axis position sets (product) when it is one.
    region = None
    if not rk.adv_axes or len(rk.adv_axes) == 1:
        region = {}
        for a in rk.out_axes:
            if a[0] == "src":
                region[a[1]] = a[2]
        for k, i in rk.drops:
            region[k] = np.array([i], I64)
        if rk.adv_axes:
            region[rk.adv_axes[0]] = rk.adv_idx[0]
        for k in range(nd):
            region.setdefault(k, np.arange(shape[k], dtype=I64))
    # Old terms minus the region: exact when the region is a product, else dropped from lo.
    lo_old, hi_old = [], list(target.hi)
    if region is not None:
        restricted = [k for k in range(nd) if len(np.unique(region[k])) < shape[k]]
        for t in target.lo:
            try:
                lo_old += _minus_region(t, shape, region, restricted)
            except (_TooBig, _Unsupported):
                flags.add("lo_dropped")
        hi_new_old = []
        for t in hi_old:
            try:
                hi_new_old += _minus_region(t, shape, region, restricted)
            except (_TooBig, _Unsupported):
                hi_new_old.append(t)
        hi_old = hi_new_old
    elif target.lo:
        flags.add("lo_dropped")
    lo, hi = [], []         # what this write adds: what the target keeps is already merged, or was when it was made
    # The value, broadcast to the indexed shape, placed at the region.
    if value is not None and not value.is_empty():
        v = broadcast(value, value_shape, rk.out_shape) if tuple(value_shape) != rk.out_shape else value
        if region is not None:
            def place(t: Term) -> Term:
                return _place_region(t, rk, shape)
            q = _map_terms(v, place, nd)
            # The value's own terms first: they share the written region, so they unite in their fixed factors
            # (one pool's days and a mask's days, say). Merged one by one into the target's terms instead, the
            # first would move its factor into an axis and each later one overlap it there, at a cost growing
            # with every write of a loop.
            lo += merge(q.lo)
            hi += merge(q.hi)
            flags |= q.flags
        else:
            c = collapse(v.hi, nd)
            if c is not None:
                hi.append(c)
            if v.lo:
                flags.add("lo_dropped")
    if key_prov is not None and not key_prov.is_empty():
        # Which elements were written depends on the key's values.
        lo += key_prov.lo
        hi += key_prov.hi
    return _cap(Prov(_merge_new(lo_old, lo), _merge_new(hi_old, hi), frozenset(flags)), nd)


def _merge_new(old, new) -> tuple[Term, ...]:
    """As _merge_parts: past a length, each write of a loop merges what it adds, not the whole list again."""
    return merge(new, onto=_clean(old)) if len(old) >= MERGE_ONTO else merge([*old, *new])


def _minus_region(t: Term, shape, region, restricted) -> list[Term]:
    """t restricted to the complement of the product region (exact, n terms)."""
    if not restricted:
        return []
    for k in restricted:
        m = t.axes[k]
        if m is not None and not m.covered()[np.asarray(region[k], I64)].any():
            return [t]          # the region misses this term entirely
    out = []
    axes0 = list(t.axes)
    for c, k in enumerate(restricted):
        axes = list(axes0)
        # axes before c: inside the region; axis k: outside; the rest: anything.
        ok = True
        for kk in restricted[:c]:
            axes[kk] = _restrict(axes[kk], shape[kk], region[kk], inside=True)
        axes[k] = _restrict(axes[k], shape[k], region[k], inside=False)
        nt = Term(tuple(axes), t.fixed)
        if ok and not nt.empty():
            out.append(nt)
    return out


def _restrict(m: AxisMap | None, n: int, positions, inside: bool) -> AxisMap:
    pos = np.unique(np.asarray(positions, I64))
    if inside:
        keep = pos
    else:
        mask = np.ones(n, bool)
        mask[pos] = False
        keep = np.nonzero(mask)[0]
    if m is None:
        return AxisMap.presence(n, keep)
    return m.take(keep).place(keep, n)


def _place_region(t: Term, rk: _Key, shape) -> Term:
    """A term over the indexed shape placed into the target's index space."""
    nd = len(shape)
    axes: list = [None] * nd
    fixed = list(t.fixed)
    vi = 0
    for a in rk.out_axes:
        m = t.axes[vi]
        vi += 1
        if a[0] == "new":
            if m is not None and m.dims:
                fixed.append((m.dims, m.union()))
            continue
        k = a[1] if a[0] == "src" else rk.adv_axes[0]
        pos = a[2] if a[0] == "src" else rk.adv_idx[0]
        if len(np.unique(pos)) != len(pos):
            raise _Unsupported
        if m is None:
            m = AxisMap.full(len(pos))
        axes[k] = m.place(pos, shape[k])
    for k, i in rk.drops:
        axes[k] = AxisMap.presence(shape[k], [i])
    # Absorb singleton fixed factors into a dropped axis, if any, so that loop
    # writes of one cell or one day each merge.
    if rk.drops and fixed:
        k = rk.drops[-1][0]
        single = [(d, r) for d, r in fixed if d and len(r) == 1]
        if single:
            axes[k] = axes[k].times(single)
            fixed = [(d, r) for d, r in fixed if not (d and len(r) == 1)]
    return Term(tuple(axes), tuple(fixed))


# --------------------------------------------------------------- merging

def _rel_equal(x: np.ndarray, y: np.ndarray) -> bool:
    return x is y or _same(x, y)


def _fixed_equal(a, b) -> bool:
    if a is b:
        return True
    return dict(a).keys() == dict(b).keys() and all(_rel_equal(r, dict(b)[d]) for d, r in a)


_UNION_CACHE: collections.OrderedDict = collections.OrderedDict()   # (id, id) -> (ma, mb, union, rows), oldest first
_UNION_CACHE_ROWS = [0]
_UNION_CACHE_MAX_ROWS = 10_000_000      # rows held by the table, inputs and results, with half a row per position: about 300 MB at most


def _union_maps(ma: AxisMap, mb: AxisMap) -> AxisMap:
    """Position by position, the union of two axis maps over the same dimensions. Remembered:
    per-cell loops union the same maps thousands of times (the entries keep their maps alive,
    so an id cannot be reused while it is in the table)."""
    key = (id(ma), id(mb))
    hit = _UNION_CACHE.get(key)
    if hit is not None:
        _UNION_CACHE.move_to_end(key)
        return hit[2]
    ca, cb = ma.covered(), mb.covered()
    if not np.any(ca & cb):
        counts = ma.counts() + mb.counts()
        pos_a, pos_b = np.nonzero(ca)[0], np.nonzero(cb)[0]
        vals = np.concatenate([ma.vals, mb.vals])
        keys = np.concatenate([np.repeat(pos_a, ma.counts()[ca]), np.repeat(pos_b, mb.counts()[cb])])
        order = np.argsort(keys, kind="stable")
        ptr = np.zeros(ma.n + 1, I64)
        np.cumsum(counts, out=ptr[1:])
        out = AxisMap(ma.dims, ptr, vals[order])
    else:
        if len(ma.vals) + len(mb.vals) > MAX_ROWS:
            raise _TooBig
        # rows (position, value...), unique, in position order; one int64 per row where it fits
        pos = np.concatenate([np.repeat(np.arange(ma.n, dtype=I64), ma.counts()),
                              np.repeat(np.arange(mb.n, dtype=I64), mb.counts())])
        vals = np.concatenate([ma.vals, mb.vals])
        if vals.shape[1] == 1 and vals.size and int(vals.min()) >= 0:
            top = int(vals.max()) + 1
            if (ma.n + 1) * top < 2**62:
                u = _uniq(pos * top + vals[:, 0])
                pos, uvals = u // top, (u % top)[:, None]
            else:
                rows = _rows_unique(np.column_stack([pos, vals]))
                pos, uvals = rows[:, 0], rows[:, 1:]
        else:
            rows = _rows_unique(np.column_stack([pos, vals]))
            pos, uvals = rows[:, 0], rows[:, 1:]
        ptr = np.zeros(ma.n + 1, I64)
        np.add.at(ptr, pos + 1, 1)
        np.cumsum(ptr, out=ptr)
        out = AxisMap(ma.dims, ptr, uvals)
    _work(len(out.vals))                       # amendment 19(b): the rows a merge produces
    # An entry also holds each map's position tables, about 17 bytes per position against about 30 per row: over a long axis those
    # are most of its size, and counting rows alone let the table reach gigabytes (the squeeze test, 2 Nov).
    n = len(ma.vals) + len(mb.vals) + len(out.vals) + (ma.n + mb.n + out.n) // 2
    if n <= _UNION_CACHE_MAX_ROWS:
        while _UNION_CACHE and _UNION_CACHE_ROWS[0] + n > _UNION_CACHE_MAX_ROWS:
            _UNION_CACHE_ROWS[0] -= _UNION_CACHE.popitem(last=False)[1][3]
        _UNION_CACHE[key] = (ma, mb, out, n)
        _UNION_CACHE_ROWS[0] += n
    return out


def _try_merge(a: Term, b: Term) -> Term | None:
    """One term for two whose units are exactly its units: (A x C) | (B x C) = (A | B) x C, position
    by position along one axis, or in one fixed factor. Everything else must be equal. A fixed
    factor that differs moves into the differing axis first, which keeps every element's units."""
    if len(a.axes) != len(b.axes):
        return None
    diff = []
    for k, (ma, mb) in enumerate(zip(a.axes, b.axes)):
        if ma is mb or (ma is not None and mb is not None and ma.equal(mb)):
            continue
        diff.append(k)
        if len(diff) > 1:
            return None
    if _fixed_equal(a.fixed, b.fixed):
        if not diff:
            return a
        k = diff[0]
        ma, mb = a.axes[k], b.axes[k]
        if ma is None or mb is None or ma.dims != mb.dims or ma.n != mb.n:
            return None
        axes = list(a.axes)
        axes[k] = _union_maps(ma, mb)
        return Term(tuple(axes), a.fixed)
    fa, fb = dict(a.fixed), dict(b.fixed)
    moved = [d for d in set(fa) | set(fb) if d not in fa or d not in fb or not _rel_equal(fa[d], fb[d])]
    if not diff:
        # the same axes: one fixed factor over the same dimensions unites directly
        if len(moved) == 1 and moved[0] in fa and moved[0] in fb:
            d = moved[0]
            united = _rows_unique(np.vstack([fa[d], fb[d]]))
            _work(len(united))                 # amendment 19(b): a merge of fixed factors produces rows too
            return Term(a.axes, tuple((x, united if x == d else r) for x, r in a.fixed))
        return None
    k = diff[0]
    ma, mb = a.axes[k], b.axes[k]
    if ma is None or mb is None or ma.n != mb.n:
        return None
    # every moved factor multiplies the rows
    rows_a, rows_b = int(ma.indptr[-1]), int(mb.indptr[-1])
    for d in moved:
        rows_a *= len(fa[d]) if d in fa else 1
        rows_b *= len(fb[d]) if d in fb else 1
    if rows_a > MERGE_MOVE_MAX_ROWS or rows_b > MERGE_MOVE_MAX_ROWS:
        return None
    na = ma.times([(d, fa[d]) for d in moved if d in fa])
    nb = mb.times([(d, fb[d]) for d in moved if d in fb])
    if set(na.dims) != set(nb.dims):
        return None
    nb = _canon(nb) if na.dims != nb.dims else nb
    na = _canon(na) if na.dims != nb.dims else na
    if na.dims != nb.dims:
        return None
    axes = list(a.axes)
    axes[k] = _union_maps(na, nb)
    return Term(tuple(axes), tuple((d, r) for d, r in a.fixed if d not in moved))


def merge(terms, onto=()) -> tuple[Term, ...]:
    """Merge terms that differ only on one axis with disjoint coverage; `onto`: terms already merged, to continue from.
    Merging only makes the list shorter, so a pair it declines or a merge it stops stays exact."""
    out: list[Term] = list(onto)
    todo = _clean(terms)
    enough = _WORK[0] + MERGE_CALL_MAX_WORK
    for at, t in enumerate(todo):
        if STOPPED[0] or _WORK[0] > enough:
            return (*out, *todo[at:])
        cur = t
        changed = True
        while changed:
            changed = False
            for idx in range(len(out) - 1, max(-1, len(out) - 9), -1):
                _work(TERM_WORK, TERMS)
                try:
                    m = _try_merge(out[idx], cur)
                except _TooBig:
                    m = None
                if m is not None:
                    cur = m
                    del out[idx]
                    changed = not STOPPED[0] and _WORK[0] <= enough
                    break
        out.append(cur)
    return tuple(out)


# --------------------------------------------------------------- coverage

def covered(terms, shape) -> np.ndarray:
    """Elements of an array of `shape` covered by at least one term."""
    shape = tuple(shape)
    cov = np.zeros(shape, bool)
    if not shape:
        return np.array(bool(_clean(terms)))
    per_axis: dict[int, np.ndarray] = {}
    for t in _clean(terms):
        restricted = [k for k, m in enumerate(t.axes) if m is not None and not m.covered().all()]
        if not restricted:
            cov[...] = True
            return cov
        if len(restricted) == 1:
            k = restricted[0]
            per_axis.setdefault(k, np.zeros(shape[k], bool))
            per_axis[k] |= t.axes[k].covered()
            continue
        cov |= t.covered(shape)
    for k, v in per_axis.items():
        sh = [1] * len(shape)
        sh[k] = shape[k]
        cov |= v.reshape(sh)
    return cov


def element_units(terms, index) -> list[tuple[tuple[str, ...], np.ndarray]]:
    """Factor lists of the terms covering one element (for tests)."""
    out = []
    for t in _clean(terms):
        fs = []
        ok = True
        for m, i in zip(t.axes, index):
            if m is None:
                continue
            row = m.take([i])
            if not row.covered()[0]:
                ok = False
                break
            if m.dims:
                fs.append((m.dims, row.vals))
        if ok:
            out.append(fs + [(d, r) for d, r in t.fixed if d])
    return out


def unit_set(factor_lists, dims) -> set[tuple]:
    """Explicit unit set of a list of factor lists, as tuples over `dims` (tests)."""
    out: set[tuple] = set()
    for fs in factor_lists:
        cols = [d for ds, _ in fs for d in ds]
        rels = [r for _, r in fs]
        for combo in itertools.product(*[list(map(tuple, r)) for r in rels]):
            flat = dict(zip(cols, [v for part in combo for v in part]))
            out.add(tuple(flat[d] for d in dims))
    return out
