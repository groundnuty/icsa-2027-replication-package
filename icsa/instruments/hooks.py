"""Library hooks of the in-sandbox tracer: install with `install()` (DESIGN.md).

The sandbox (#7) loads this at interpreter start, e.g. from `sitecustomize`:

    import icsa.instruments.hooks as _h; _h.install_from_env()

`ICSA_TRACE_DIR` (required, the run's trace directory, copied out after the
run) switches it on; `ICSA_OUTPUT_DIR` is the run's output directory.
"""
from __future__ import annotations

import atexit
import builtins
import dataclasses
import errno as _errno
import functools
import hashlib
import inspect
import io
import json
import posixpath
import os
import re
import stat
import subprocess
import sys
import sysconfig
import threading
import time
import zlib
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import numpy as np
import numpy.ma  # noqa: F401  (import before patching: numpy.ma calls np.array on import)

from . import prov as P
from . import config
from . import tracer as T

builtins_open = builtins.open        # as at import: agent code that rebinds open() cannot reach this path
_INSTALLED = False
_mem_ds: dict[int, str] = {}
_fileobj_ident: dict[str, str] = {}
_tl = threading.local()


_bytes_src: dict[int, tuple[str, int, int]] = {}   # id(bytes) -> (identity, length, crc32)


@T._timed
def _register_bytes(buf, ident: str):
    if isinstance(buf, bytes) and len(buf) >= 64:
        _bytes_src[id(buf)] = (ident, len(buf), zlib.crc32(buf))


@T._timed
def _bytes_ident(buf) -> str | None:
    """The identity of bytes read whole from a dataset file, verified by length and CRC."""
    if not isinstance(buf, bytes):
        return None
    e = _bytes_src.get(id(buf))
    if e is None or e[1] != len(buf) or e[2] != zlib.crc32(buf):
        return None
    return e[0]


@T._timed
def _content_ident(src) -> str | None:
    """The identity of an in-memory source by its content: "sha256:<hex>:<length>" of the whole buffer (bytes,
    bytearray, memoryview, a BytesIO's buffer). The same in every option, whatever moved the bytes (an fsspec
    read, a download, a local read, a copy): offline it names the dataset file with that content, and modified
    or mixed bytes name none, so the source is unidentified."""
    try:
        if hasattr(src, "getbuffer"):
            with src.getbuffer() as mv:
                return _hash_view(mv)
        with memoryview(src) as mv:
            return _hash_view(mv)
    except Exception:  # noqa: BLE001 - not a buffer: no content identity
        return None


def _hash_view(mv) -> str | None:
    if not mv.contiguous:
        return None
    with (mv.cast("B") if mv.format != "B" or mv.ndim != 1 else mv) as b:
        return f"sha256:{hashlib.sha256(b).hexdigest()}:{b.nbytes}"


# --------------------------------------------------------------- local files
# The identity of a local file reached by path (Tracer #2, science, #2, 05:26Z). The dataset's own mount is read-only and
# names itself. A file anywhere else is the agent's, on a disk it can write: its name says nothing, however it matches the
# index. So it is a recorded download while it is unchanged, or else what its content says:
#   a download: the remote identity while the file has the (device, inode, size, mtime) recorded when it arrived. The
#     records are read from the trace directory, since each Sandbox.exec is a new interpreter. A file that differs is
#     never hashed (a cost in the agent's time, for an answer already known): `modified:`, which resolves to nothing.
#   opened for writing in this process: `modified:` at once, since what is written can be in a cache and not yet on disk.
#   any other file: "sha256:<hex>:<length>" of its content, as for an in-memory source, computed once per file state and
#     recorded. A copy of the dataset is the dataset, and anything else names nothing.
# The check is one stat per read, on the agent's own disk; a read on the mount makes no extra call.
@dataclasses.dataclass
class _LocalFile:
    t: float
    size: int
    mtime_ns: int
    ident: str
    download: bool


_local_files: dict[tuple[int, int], _LocalFile] = {}     # (device, inode) -> what is on record
_download_paths: dict[str, tuple[int, int]] = {}         # realpath -> the download recorded there last
_written: set[str] = set()                               # realpaths opened for writing in this process
_local_streams_read: dict[str, int] = {}                 # stream file -> bytes read so far


def _note_local_file(rec: dict) -> None:
    key = (rec["st"][0], rec["st"][1])
    cur = _local_files.get(key)
    if cur is None or rec["t"] >= cur.t:
        _local_files[key] = _LocalFile(rec["t"], rec["st"][2], rec["st"][3], rec["ident"], rec["download"])
    if rec["download"]:
        _download_paths[rec["path"]] = key


def _read_stream_records(pattern: str, note) -> None:
    """What the run's processes put on record in a stream: every line since the last look. Called only when a file is not
    known."""
    st = T._STATE
    if st is None:
        return
    try:
        for f in st.dir.glob(pattern):
            name, seen = str(f), _local_streams_read.get(str(f), 0)
            with builtins_open(f, "rb") as fh:
                fh.seek(seen)
                data = fh.read()
            end = data.rfind(b"\n") + 1            # a line being written is taken next time
            for line in data[:end].splitlines():
                try:
                    note(json.loads(line))
                except (ValueError, KeyError, TypeError, IndexError):
                    T._count("torn_trace")
            _local_streams_read[name] = seen + end
    except OSError:
        T._count("internal_error")


def _read_local_records() -> None:
    _read_stream_records("localfiles.*.jsonl", _note_local_file)


def _record_local_file(rp: str, s: os.stat_result, ident: str, download: bool) -> None:
    rec = {"t": time.time(), "path": rp, "st": [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns], "ident": ident,
           "download": download}
    _note_local_file(rec)
    st = T._STATE
    if st is not None:
        st._write("localfiles", rec)


def _record_download(rp: str, ident: str) -> None:
    """A file has just arrived whole at `rp`. Whatever it was before, it is the remote file now."""
    _written.discard(rp)
    try:
        _record_local_file(rp, os.stat(rp), ident, True)
    except OSError:
        T._count("internal_error")


def _hash_file(rp: str) -> str | None:
    h = hashlib.sha256()
    try:
        with builtins_open(rp, "rb", buffering=0) as f:
            buf = bytearray(4 << 20)
            n = 0
            while True:
                k = f.readinto(buf)
                if not k:
                    return f"sha256:{h.hexdigest()}:{n}"
                h.update(memoryview(buf)[:k])
                n += k
    except OSError:
        return None


def _local_ident(rp: str) -> str:
    if rp in _written:
        return "modified:" + rp
    try:
        s = os.stat(rp)
    except OSError:
        return "local:" + rp
    key, stamp = (s.st_dev, s.st_ino), (s.st_size, s.st_mtime_ns)
    e = _local_files.get(key)
    if e is None or (e.size, e.mtime_ns) != stamp:
        _read_local_records()               # another process's record, or a newer one
        e = _local_files.get(key)
    if e is not None and (e.size, e.mtime_ns) == stamp:
        return e.ident
    if (e is not None and e.download) or _download_paths.get(rp, key) != key:
        return "modified:" + rp             # a recorded download that changed, or another file at its path
    ident = _hash_file(rp)
    if ident is None:
        return "local:" + rp
    _record_local_file(rp, s, ident, False)
    return ident


def _note_write_open(path) -> None:
    """A local file opened for writing by a data library: what is written can be read back through the same handle
    before anything reaches the disk, so no check of the disk can see it."""
    try:
        _written.add(os.path.realpath(os.fspath(path)))
    except TypeError:
        pass                                # a file object


_resolved_roots: dict[tuple, tuple] = {}


def _on_data_root(rp: str) -> bool:
    """Whether a resolved path lies on the dataset's own mount. The roots are resolved once per process: resolving one
    looks up each of its components, which on the mount is traffic that only M would have."""
    roots = _data_roots()
    q = rp.rstrip(os.sep) + os.sep
    if q.startswith(roots):
        return True
    if not roots:
        return False
    resolved = _resolved_roots.get(roots)
    if resolved is None:
        resolved = _resolved_roots[roots] = tuple(os.path.realpath(r).rstrip(os.sep) + os.sep for r in roots)
    return q.startswith(resolved)


@T._timed
def _ident_for_path(path) -> str:
    try:
        rp = os.path.realpath(os.fspath(path))
    except TypeError:
        return "unknown:" + repr(path)
    return "path:" + rp if _on_data_root(rp) else _local_ident(rp)


def _fs_ident(fs, path) -> str:
    proto = getattr(fs, "protocol", None)
    proto = proto[0] if isinstance(proto, (tuple, list)) else proto
    try:
        path = fs._strip_protocol(path)
    except Exception:  # noqa: BLE001
        pass
    return f"fsspec:{proto or '?'}:{path}"


def _ident_for_fileobj(obj) -> str:
    if hasattr(obj, "getbuffer"):
        c = _content_ident(obj)
        if c:
            return c
    src = getattr(obj, "_icsa_src", None)
    if src:
        return src
    if getattr(obj, "fs", None) is not None and isinstance(getattr(obj, "path", None), str):
        return _fs_ident(obj.fs, obj.path)
    for attr in ("path", "full_name", "name"):
        v = getattr(obj, attr, None)
        if isinstance(v, str) and v:
            proto = getattr(getattr(obj, "fs", None), "protocol", None)
            proto = proto[0] if isinstance(proto, (tuple, list)) else proto
            if attr == "name" and proto is None:
                return _ident_for_path(v) if os.path.exists(v) else "mem:" + v
            return f"fsspec:{proto or '?'}:{v}"
    return "mem:" + type(obj).__name__


@T._timed
def _under_output(path: str) -> bool:
    st = T._STATE
    if st is None or st.out is None or not path:
        return False
    try:
        return Path(os.path.realpath(path)).is_relative_to(st.out)
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------- data errors
# An error that leaves a data access the agent made (an open, a read or a listing, through
# h5py, netCDF4, fsspec, or the OS on the dataset's mount) is written to the `errors` stream
# and re-raised unchanged, the same in every option: one definition of "the agent saw a
# data-path error, of any origin" (#7, #14; analyse.data_errors; never a label input).
#
# Only the outermost wrapped call records, so an error a library catches inside (fsspec's
# exists() over info(), find() over a failing ls()) is not one the agent saw; the first error
# of the inner calls is kept, for the facts the outer exception lost (h5py over a file object).
#
# What counts is what the libraries really raise: OSError and everything built on it (requests'
# errors); the platform client's OnedataError family, which is not an OSError (a 502 is
# OnedataRESTError(502)); urllib3's and http.client's errors; netCDF4's read failures, a
# RuntimeError("NetCDF: ..."). A bad argument (ValueError, IndexError, ...) is not a data error.
#
# errno: from the exception, Onedata's error body (400 {id: posix, details: {errno: "eio"}}),
# the message (HDF5: "errno = 5, error message = '...'"), or a cause inside the call; null when
# none holds one, never guessed. An exception that was already being handled when the call began
# is not a cause. caused_by_agent: what the request itself brought about, by errno, else by HTTP
# status, else by exception type or a refusal's words. A refusal (EACCES, EPERM, HTTP 401, 403) is
# the agent's only on a write or outside the study's data path: on a read inside it, it can
# mean our read-only token failed or expired mid-run (science, #7, 1 Nov 16:29Z).
_ERRNO_RX = (re.compile(r"\berrno\s*=\s*(\d+)"), re.compile(r"\[Errno\s+(\d+)\]"))
_AGENT_ERRNOS = frozenset(getattr(_errno, n) for n in (
    "ENOENT", "ENOTDIR", "EISDIR", "EEXIST", "ENAMETOOLONG", "EROFS",   # a path that is not what was asked
    "ENOSPC", "EDQUOT", "EMFILE", "ENFILE") if hasattr(_errno, n))      # the agent's own disk or handles
_REFUSAL_ERRNOS = frozenset((_errno.EACCES, _errno.EPERM))
_REFUSAL_STATUSES = frozenset((401, 403))
# the rest of 4xx is the request's fault, except where the client did nothing wrong
_NOT_AGENT_4XX = frozenset((408, 425, 429))
_AGENT_TYPES = (FileNotFoundError, NotADirectoryError, IsADirectoryError, FileExistsError)
_AGENT_NAMES = frozenset(("SpaceNotFoundError", "ReadonlyTokenError"))
_ERROR_MODULES = frozenset(("onedatafilerestclient.errors", "urllib3.exceptions", "http.client",
                            "aiohttp.client_exceptions"))
_NETCDF_REQUEST_TEXTS = ("Not a valid ID", "Index exceeds", "Start+count", "Invalid argument", "Invalid dimension",
                         "not found", "Permission denied", "No such file")


def _chain(e, ambient):
    """e and its causes inside the call: never the exception being handled when it began."""
    seen: set[int] = set()
    x = e
    while x is not None and x is not ambient and id(x) not in seen and len(seen) < 8:
        seen.add(id(x))
        yield x
        x = x.__cause__ if x.__cause__ is not None else (None if x.__suppress_context__ else x.__context__)


def _named_errno(v) -> int | None:
    n = getattr(_errno, v.upper(), None) if isinstance(v, str) and v.isidentifier() else None
    return n if isinstance(n, int) else None


def os_errno(e: BaseException, ambient=None) -> tuple[int | None, str | None]:
    """The OS error number e carries, and where it was found: its errno attribute ("exception"),
    an error body ("details"), its message ("message"), or a cause's ("cause"); (None, None)
    when none is an OS error number."""
    for x in _chain(e, ambient):
        n = getattr(x, "errno", None)
        if isinstance(n, int) and not isinstance(n, bool) and n in _errno.errorcode:
            return n, "exception" if x is e else "cause"
        details = getattr(x, "details", None)
        n = _named_errno(details.get("errno")) if isinstance(details, dict) else None
        if n is not None:
            return n, "details" if x is e else "cause"
        text = str(x)
        for rx in _ERRNO_RX:
            m = rx.search(text)
            if m and int(m.group(1)) in _errno.errorcode:
                return int(m.group(1)), "message" if x is e else "cause"
    return None, None


def _client_response_status(x: BaseException) -> int | None:
    """A failure inside the shipped client's HTTP layer (onedatafilerestclient 25.0.0): on a 403 its
    debug log takes len() of a GET's empty body, so a TypeError reaches the agent instead of the
    OnedataRESTError (icsa.sandbox.gatepolicy notes it too). The status is in that frame."""
    tb, last = x.__traceback__, None
    while tb is not None:
        last, tb = tb, tb.tb_next
    if last is None or last.tb_frame.f_globals.get("__name__") != "onedatafilerestclient.http_client":
        return None
    v = getattr(last.tb_frame.f_locals.get("response"), "status_code", None)
    return v if isinstance(v, int) and not isinstance(v, bool) and 400 <= v <= 599 else None


def http_status(e: BaseException, ambient=None) -> int | None:
    """The HTTP status e or a cause carries (the platform client's http_code, requests'
    response, urllib's code); None when there is none."""
    for x in _chain(e, ambient):
        resp = getattr(x, "response", None)
        for v in (getattr(x, "http_code", None), getattr(x, "status_code", None), getattr(x, "status", None),
                  getattr(x, "code", None), getattr(resp, "status_code", None), _client_response_status(x)):
            if isinstance(v, int) and not isinstance(v, bool) and 100 <= v <= 599:
                return v
    return None


def _is_data_error(e: BaseException) -> bool:
    try:
        if isinstance(e, OSError):
            return True
        if isinstance(e, RuntimeError) and str(e).startswith("NetCDF:"):
            return True
        return any(c.__module__ in _ERROR_MODULES for c in type(e).__mro__) or _client_response_status(e) is not None
    except Exception:  # noqa: BLE001
        return False


_CONTAINER_ENV: dict[str, str] = {}


def _sandbox_env(name: str) -> str | None:
    """What the sandbox set, for a process whose environment was scrubbed: what the container itself was started with, from pid 1,
    which is the agent's own user. Without it a scrubbed child takes the mount for an ordinary local file and hashes what it opens,
    which is reads on the data path that only it would make. Read only when the process's own environment lacks the name."""
    v = os.environ.get(name)
    if v:
        return v
    if not _CONTAINER_ENV:
        _CONTAINER_ENV["\0read"] = ""
        try:
            with builtins.open("/proc/1/environ", "rb") as f:
                _CONTAINER_ENV.update(x.split("=", 1) for x in os.fsdecode(f.read()).split("\0") if "=" in x)
        except OSError:
            pass
    return _CONTAINER_ENV.get(name)


def _inside_data_path(path: str, local: str | None) -> bool | None:
    """Whether a recorded path lies in the study's data path, from what the sandbox set: the mount
    (ICSA_MOUNT_PATH, an absolute ICSA_DATASET_LOCATION) or, for the REST client, the space that
    begins a relative ICSA_DATASET_LOCATION. None when that cannot be said."""
    roots = _data_roots()
    loc = _sandbox_env("ICSA_DATASET_LOCATION")
    space = loc.strip("/").split("/", 1)[0] if loc and not os.path.isabs(loc) else None
    if not roots and not space:
        return None
    if path.startswith("mem:") or path == "?":
        return None
    if path.startswith("fsspec:"):
        rest = path.split(":", 2)[-1].strip("/")
        if space and (rest == space or rest.startswith(space + "/")):
            return True
        local = "/" + rest                  # a path of another protocol, or a local file through fsspec
    if not local:
        return None
    q = os.path.abspath(local).rstrip(os.sep) + os.sep
    return any(q.startswith(r) for r in roots)


def _caused_by_agent(e, inner, n, status, write: bool, inside: bool | None) -> bool:
    own_refusal = write or inside is False
    if n is not None:
        return own_refusal if n in _REFUSAL_ERRNOS else n in _AGENT_ERRNOS
    if status is not None:
        if status in _REFUSAL_STATUSES:
            return own_refusal
        return 400 <= status < 500 and status not in _NOT_AGENT_4XX
    for x in (e, inner):
        if x is None:
            continue
        if isinstance(x, PermissionError):
            return own_refusal
        if isinstance(x, _AGENT_TYPES) or type(x).__name__ in _AGENT_NAMES or config.D_REFUSAL_TEXT in str(x):
            return True
    return isinstance(e, RuntimeError) and any(t in str(e) for t in _NETCDF_REQUEST_TEXTS)


def _record_error(op: str, call: str, path: str, local: str | None, write: bool, e, ambient, inner):
    st = T._STATE
    if st is None:
        return
    try:
        n, src = os_errno(e, ambient)
        if n is None and inner is not None:
            n, src = os_errno(inner, ambient)[0], "inner"
            src = src if n is not None else None
        status = http_status(e, ambient)
        if status is None and inner is not None:
            status = http_status(inner, ambient)
        code = getattr(e, "errno", None)
        inside = _inside_data_path(path, local)
        st._write("errors", {
            "t": time.time(), "op": op, "call": call, "path": path, "write": write, "data_path": inside,
            "errno": n, "errname": _errno.errorcode.get(n) if n is not None else None, "errno_from": src,
            "http_status": status,
            "lib_code": code if isinstance(code, int) and not isinstance(code, bool) and code != n else None,
            "caused_by_agent": _caused_by_agent(e, inner, n, status, write, inside),
            "exc": f"{type(e).__module__}.{type(e).__qualname__}", "message": str(e),
            "inner_exc": f"{type(inner).__module__}.{type(inner).__qualname__}" if inner is not None else None,
            "inner_message": str(inner) if inner is not None else None,
            "output": bool(local) and _under_output(local)})
    except Exception:  # noqa: BLE001 - never into agent code; never a label input
        T._count("error_record_failed")


def _guarded(op, call, where, shield, step, write=None):
    """Run step() as a data call: one level deeper; an error leaving the outermost level is
    recorded (unless a shield) and re-raised as it is. An inner call's error is remembered:
    the outer call may have lost its facts, or turned it into something else."""
    d = getattr(_tl, "data_depth", 0)
    if d == 0:
        _tl.data_ambient = sys.exc_info()[1]
        _tl.data_inner = None
    _tl.data_depth = d + 1
    try:
        return step()
    except Exception as e:
        inner = getattr(_tl, "data_inner", None)
        if d > 0:
            if inner is None and _is_data_error(e):
                _tl.data_inner = e
        elif not shield and (_is_data_error(e)
                             or (inner is not None and not isinstance(e, (StopIteration, StopAsyncIteration)))):
            try:
                path, local = where()
                wr = bool(write()) if write is not None else False
            except Exception:  # noqa: BLE001
                path, local, wr = "?", None, False
            _record_error(op, call, str(path), local, wr, e, getattr(_tl, "data_ambient", None),
                          inner if inner is not e else None)
        raise
    finally:
        _tl.data_depth = d
        if d == 0:
            _tl.data_ambient = _tl.data_inner = None


class _IterGuard:
    """An iterator a data call returned (a generator, os.scandir's iterator): advancing it
    is part of the call, so a listing that fails while iterating is recorded, and the
    calls it makes inside are not the outermost."""
    __slots__ = ("_it", "_op", "_call", "_where", "_shield")

    def __init__(self, it, op, call, where, shield):
        self._it, self._op, self._call, self._where, self._shield = it, op, call, where, shield

    def __iter__(self):
        return self

    def __next__(self):
        if T._STATE is None:
            return next(self._it)
        return _guarded(self._op, self._call, self._where, self._shield, lambda: next(self._it))

    def __getattr__(self, name):            # gi_frame, ...; only what the iterator has
        attr = getattr(self._it, name)
        if name not in ("send", "throw", "close"):
            return attr

        def step(*a, **k):                  # these advance a generator too
            if T._STATE is None:
                return attr(*a, **k)
            return _guarded(self._op, self._call, self._where, self._shield, lambda: attr(*a, **k))
        return step


class _IterGuardCM(_IterGuard):
    """_IterGuard of an iterator that is also a context manager (os.scandir's)."""
    __slots__ = ()

    def __enter__(self):
        self._it.__enter__()
        return self

    def __exit__(self, *exc):
        return self._it.__exit__(*exc)


def _data_call(op: str, call: str, where, fn, *, shield: bool = False, iterates: bool = False, write=None):
    """fn wrapped: a data error leaving the outermost wrapped data call is recorded (where(a, k)
    gives the path as recorded and the local path, if any, for the output check), then
    re-raised as it is. A shield only marks the depth: errors under it are not recorded
    (it catches them itself, or raises them through its own outer caller). With iterates,
    an iterator fn returns is guarded too: advancing it is part of the call. write(a, k):
    whether the call writes (a refusal of a write is the agent's own)."""
    def wrapped(*a, **k):
        if T._STATE is None:
            return fn(*a, **k)
        r = _guarded(op, call, lambda: where(a, k), shield, lambda: fn(*a, **k),
                     (lambda: write(a, k)) if write is not None else None)
        if iterates and hasattr(r, "__next__"):
            cls = _IterGuardCM if hasattr(r, "__enter__") else _IterGuard
            return cls(r, op, call, lambda: where(a, k), shield)
        return r
    wrapped.__name__ = getattr(fn, "__name__", "wrapped")
    wrapped.__doc__ = getattr(fn, "__doc__", None)
    wrapped._icsa = True
    return wrapped


def _local(x) -> str | None:
    try:
        return os.fsdecode(x)
    except TypeError:
        return None


def _h5_target(name):
    """(path as recorded, local path) of what h5py.File was given: a path, or a file object."""
    if hasattr(name, "read") and hasattr(name, "seek"):
        return _ident_for_fileobj(name), None
    return (_local(name),) * 2


def _h5_read_target(a, k):
    """(path as recorded, local path) of a dataset being read: h5py names a file object by
    its repr, so a remote file keeps the identity remembered when it was opened."""
    fn = a[0].file.filename
    ident = _fileobj_ident.get(fn)
    return (ident, None) if ident else (fn, fn)


def _nc_target(a, k):
    g = a[0].group()
    while getattr(g, "parent", None) is not None:
        g = g.parent
    try:
        p = g.filepath()
    except ValueError:
        return "mem:netCDF4", None
    return p, p


# Where the dataset is a local path (M, M+: the mount): OS-level listings there are data
# listings. Elsewhere (the agent's own files, D's downloaded copies) they are not.
def _data_roots() -> tuple[str, ...]:
    roots = []
    for v in (_sandbox_env("ICSA_MOUNT_PATH"), _sandbox_env("ICSA_DATASET_LOCATION")):
        if v and os.path.isabs(v):
            roots.append(os.path.abspath(v).rstrip(os.sep) + os.sep)
    return tuple(roots)


def _path_text(p) -> str | None:
    try:
        return os.fsdecode(p)
    except TypeError:
        return None                           # a file descriptor, or not a path


def _patch_os():
    """OS-level listings on the dataset's local path (the mount in M and M+). The callers
    that catch listing errors themselves (glob, os.walk, pathlib's iteration and globbing)
    are wrapped as the outer call, so only what escapes them is recorded; on other paths
    they only mark the depth."""
    roots = _data_roots()
    if not roots:
        return

    def on_data(p) -> bool:
        t = _path_text(p)
        if t is None:
            return False
        try:
            q = os.path.abspath(t).rstrip(os.sep) + os.sep
        except Exception:  # noqa: BLE001
            return False
        return any(q.startswith(r) for r in roots)

    def guard(owner, name, call, path_of, iterates, direct_off_data):
        orig = getattr(owner, name)

        def where(a, k):
            t = _path_text(path_of(a, k))
            return t, t
        rec = _data_call("list", call, where, orig, iterates=iterates)
        shield = _data_call("list", call, where, orig, shield=True, iterates=iterates)

        def wrapped(*a, **k):
            if T._STATE is None:
                return orig(*a, **k)
            try:
                p = path_of(a, k)
            except Exception:  # noqa: BLE001
                p = None
            if p is not None and on_data(p):
                return rec(*a, **k)
            return orig(*a, **k) if direct_off_data else shield(*a, **k)
        wrapped.__name__ = name
        wrapped.__qualname__ = getattr(orig, "__qualname__", name)
        wrapped.__doc__ = orig.__doc__
        wrapped._icsa = True
        setattr(owner, name, wrapped)

    def first(key, default="."):
        return lambda a, k: a[0] if a else k.get(key, default)

    def self_path(a, k):
        return a[0]

    def glob_path(a, k):
        return k.get("root_dir") or (a[0] if a else k.get("pathname"))

    # the listing calls themselves: off the data path, untouched
    guard(os, "listdir", "os.listdir", first("path"), False, True)
    guard(os, "scandir", "os.scandir", first("path"), True, True)
    # callers that catch listing errors themselves
    guard(os, "walk", "os.walk", first("top"), True, False)
    import glob as _glob
    import pathlib as _pathlib
    guard(_glob, "glob", "glob.glob", glob_path, False, False)
    guard(_glob, "iglob", "glob.iglob", glob_path, True, False)
    for name in ("iterdir", "glob", "rglob", "walk"):
        if callable(getattr(_pathlib.Path, name, None)):
            guard(_pathlib.Path, name, f"pathlib.Path.{name}", self_path, True, False)


# --------------------------------------------------------------- listing requests
# requests.Session.send is the one choke point of the shipped client and of an agent's own
# requests calls. Each listing request goes to the `http` stream, in the proxy log's schema
# (DESIGN.md), with who made it. Same response, same object; a listing's body is parsed here
# only if requests already holds it. httpx, urllib and subprocesses do not pass here: the gate
# log sees them, and the cross-check compares the two (crosscheck.py).
_CHILDREN_RX = re.compile(r"/data/([^/]+)/children$")
_SKIP_FRAMES = ("requests", "urllib3", "icsa.instruments.hooks", "icsa.instruments.tracer")
_CLIENT_FRAMES = ("onedatafilerestclient", "onedatarestfsspec", "fsspec", "icsa_option_shims",
                  "icsa.instruments.sim")


def _module_in(name: str, packages) -> bool:
    return any(name == p or name.startswith(p + ".") for p in packages)


def _http_caller() -> str:
    """Whose code asked: the first frame outside requests and the tracer."""
    f = sys._getframe(1)
    while f is not None and _module_in(f.f_globals.get("__name__", ""), _SKIP_FRAMES):
        f = f.f_back
    return "client" if f is not None and _module_in(f.f_globals.get("__name__", ""), _CLIENT_FRAMES) else "agent"


def _record_listing(request, response, stream: bool):
    st = T._STATE
    if st is None:
        return
    try:
        parts = urlsplit(request.url)
        m = _CHILDREN_RX.search(parts.path)
        if m is None and not (parts.path == "/list" or parts.path.startswith("/list/")):
            return
        q = parse_qs(parts.query)
        limit = q.get("limit", [None])[0]
        rec = {"t": time.time(), "kind": "list", "method": request.method, "url_path": parts.path,
               "dir_id": m.group(1) if m else None,
               "dir": None if m else unquote(parts.path[len("/list"):].strip("/")),
               "limit": int(limit) if limit and limit.isdigit() else limit, "token": q.get("token", [None])[0],
               "status": None if response is None else response.status_code,
               "is_last": None, "next_token": None, "entries": None, "caller": _http_caller()}
        if response is not None and response.status_code == 200 and request.method == "GET" and not stream:
            page = response.json()
            rec.update(is_last=page.get("isLast"), next_token=page.get("nextPageToken"),
                       entries=len(page.get("children", ())))
        st._write("http", rec)
    except Exception:  # noqa: BLE001 - never into agent code
        T._count("listing_record_failed")


def _patch_requests():
    import requests
    send = requests.Session.send

    def wrapped(self, request, **kw):
        if T._STATE is None:
            return send(self, request, **kw)
        try:
            r = send(self, request, **kw)
        except Exception:
            _record_listing(request, None, False)
            raise
        _record_listing(request, r, bool(kw.get("stream")))
        return r
    wrapped.__name__ = "send"
    wrapped.__doc__ = send.__doc__
    wrapped._icsa = True
    requests.Session.send = wrapped
    T._STATE._write("events", {"t": time.time(), "kind": "listing_hook"})


def _is_dataset_file(path) -> bool:
    """Whether a file is the dataset's, by what is known without reading it: on its mount, or a recorded download unchanged."""
    try:
        rp = os.path.realpath(os.fspath(path))
    except TypeError:
        return False
    if _on_data_root(rp):
        return True
    if rp in _written:
        return False
    try:
        s = os.stat(rp)
    except OSError:
        return False
    e = _local_files.get((s.st_dev, s.st_ino))
    if e is None:
        _read_local_records()
        e = _local_files.get((s.st_dev, s.st_ino))
    return e is not None and e.download and (e.size, e.mtime_ns) == (s.st_size, s.st_mtime_ns)


def _other_variable(r, path):
    """A coordinate or any other variable the agent's own code read from the dataset (`path` None: a remote file object): not
    the data, so a tracked-type array holding nothing tracked, as np.zeros is: a write into it is seen, and it is no plain
    operand. From the agent's own files it stays plain: it may hold what nothing named. The caller, under the data-call
    wrapper's frames: this function, the hook, its step, _guarded, wrapped."""
    if isinstance(r, np.ndarray) and r.ndim and type(r) in (np.ndarray, np.ma.MaskedArray) and T._is_agent_frame(6) \
            and (path is None or _is_dataset_file(path)):
        return T._wrap(r, P.Prov.none())       # for a masked array (netCDF4's by default): its provenance, empty
    return r


# --------------------------------------------------------------- h5py

def _patch_h5py():
    import h5py

    file_init = h5py.File.__init__

    def init(self, name, *a, **k):
        file_init(self, name, *a, **k)
        try:
            mode = a[0] if a else k.get("mode", "r")
            if mode not in (None, "r") and T._STATE is not None:
                _note_write_open(name)
            if hasattr(name, "read") and hasattr(name, "seek"):
                # a buffer opened for writing can change under its content identity: never identified
                _fileobj_ident[self.filename] = (_ident_for_fileobj(name) if mode in (None, "r")
                                                 else "mem:writable:" + type(name).__name__)
            if mode in ("w", "w-", "x") and _under_output(self.filename):
                _sink_event("open_w", self.filename)
        except Exception:  # noqa: BLE001
            T._count("internal_error")
    h5py.File.__init__ = _data_call(
        "open", "h5py.File",
        lambda a, k: _h5_target(a[1] if len(a) > 1 else k.get("name")), init,
        write=lambda a, k: (a[2] if len(a) > 2 else k.get("mode", "r")) not in (None, "r"))

    def ident(dset) -> str:
        fn = dset.file.filename
        return _fileobj_ident.get(fn) or _ident_for_path(fn)

    getitem = h5py.Dataset.__getitem__

    def h5_getitem(self, args, new_dtype=None):
        r = getitem(self, args, new_dtype=new_dtype)
        if T._STATE is None:
            return r
        try:
            fn = self.file.filename
            if _is_out(fn) and not getattr(_tl, "xr_write", False):
                _reread(fn)
        except Exception:  # noqa: BLE001
            T._count("internal_error")
        if self.name.rsplit("/", 1)[-1] == T.VAR and not getattr(_tl, "inner", False):
            return T.ledger("h5py", ident(self), self.shape, args, r)
        fn = self.file.filename
        return _other_variable(r, None if fn in _fileobj_ident else fn)
    h5py.Dataset.__getitem__ = _data_call("read", "h5py.Dataset.__getitem__", _h5_read_target, h5_getitem)

    read_direct = h5py.Dataset.read_direct

    def h5_read_direct(self, dest, source_sel=None, dest_sel=None):
        if T._STATE is not None:
            try:                            # Dataset.__array__ reads through read_direct too
                fn = self.file.filename
                if _is_out(fn) and not getattr(_tl, "xr_write", False):
                    _reread(fn)
            except Exception:  # noqa: BLE001
                T._count("internal_error")
        _tl.inner = True
        try:
            read_direct(self, T._unwrap(dest) if isinstance(dest, T.TArray) else dest, source_sel, dest_sel)
        finally:
            _tl.inner = False
        if T._STATE is None:
            return
        dkey = dest_sel if dest_sel is not None else Ellipsis
        if self.name.rsplit("/", 1)[-1] != T.VAR:
            # Another dataset's values overwrote that region of dest: it now carries
            # no provenance, and other views of dest are stale.
            try:
                got_shape = np.shape(np.ndarray.__getitem__(T._plain(dest) if isinstance(dest, T.TArray)
                                                            else np.asarray(dest), dkey))
                if isinstance(dest, T.TArray):
                    dest._p = P.setitem(dest._p, dest.shape, dkey, None, got_shape)
                T._invalidate(dest, None)
            except Exception:  # noqa: BLE001
                if isinstance(dest, T.TArray):
                    T._mutated(dest, [], overwrite=False)
                T._count("internal_error")
            return
        sel = source_sel if source_sel is not None else Ellipsis
        try:
            got = np.ndarray.__getitem__(np.asarray(T._unwrap(dest)).view(np.ndarray), dkey)
            tagged = T.ledger("h5py.read_direct", ident(self), self.shape, sel, got)
            vp = getattr(tagged, "_p", None)
            if isinstance(dest, T.TArray) and vp is not None:
                dest._p = P.setitem(dest._p, dest.shape, dkey, vp, np.shape(got))
            else:
                T._count("untagged_materialisation")
                T._escape_prov(vp, "read_direct_plain")
            T._invalidate(dest, vp)
        except Exception:  # noqa: BLE001
            if isinstance(dest, T.TArray):
                T._mutated(dest, [], overwrite=False)
            T._count("internal_error")
    h5py.Dataset.read_direct = _data_call("read", "h5py.Dataset.read_direct", _h5_read_target, h5_read_direct)

    setitem = h5py.Dataset.__setitem__

    def h5_setitem(self, args, val):
        if T._STATE is None or not _under_output(self.file.filename):
            return setitem(self, args, val)
        var = _h5_var(self)
        xr = getattr(_tl, "xr_write", False)
        rec, a2, v2 = _sink_begin("h5py", self.file.filename, var, args, val)
        rec = None if xr else rec
        r = setitem(self, a2, v2)
        if not xr:
            _mirror(rec, self.file.filename, var, a2, v2, var_shape=self.shape, dtype=self.dtype)
        _commit(rec)
        return r
    h5py.Dataset.__setitem__ = h5_setitem

    create = h5py.Group.create_dataset

    def h5_create(self, name, shape=None, dtype=None, data=None, **kw):
        if T._STATE is None or not _under_output(self.file.filename):
            return create(self, name, shape=shape, dtype=dtype, data=data, **kw)
        var = posixpath.join(self.name, str(name)).lstrip("/")
        xr = getattr(_tl, "xr_write", False)
        if data is None:
            # A new (possibly re-created) variable holds its fill value: an untracked write
            # of the whole variable, so nothing written to an earlier one survives.
            d = create(self, name, shape=shape, dtype=dtype, data=data, **kw)
            if not xr and name is not None:
                try:
                    try:
                        fill = np.full(d.shape, kw.get("fillvalue") or 0, d.dtype)
                    except Exception:  # noqa: BLE001
                        fill = None
                    dn = (d.name or var).lstrip("/")
                    rec = _sink_write("h5py.create", self.file.filename, dn, None, Ellipsis,
                                      fill if fill is not None else np.zeros(0))
                    _mirror(rec, self.file.filename, dn, Ellipsis, fill, full=True)
                    _commit(rec)
                except Exception:  # noqa: BLE001
                    T._count("internal_error")
            return d
        # recorded before the create, while the value's provenance is as the agent made it
        rec, _, d2 = _sink_begin("h5py.create", self.file.filename, var, Ellipsis, data)
        rec = None if xr else rec
        d = create(self, name, shape=shape, dtype=dtype, data=d2, **kw)
        try:
            if name is None:
                rec = None                  # an anonymous dataset is in no variable
            elif not xr:
                _mirror(rec, self.file.filename, (d.name or var).lstrip("/"), Ellipsis, d2,
                        full=True, dtype=d.dtype, var_shape=d.shape)
            _commit(rec)
        except Exception:  # noqa: BLE001
            T._count("internal_error")
        return d
    h5py.Group.create_dataset = h5_create

    # Replacing a sink variable by link operations (del, move, copy) writes values the
    # hooks do not see: its recorded provenance no longer holds, whatever the values.
    @T._timed
    def _replaced(group, name):
        try:
            if isinstance(name, bytes):
                name = name.decode("utf-8", "replace")
            if T._STATE is None or not isinstance(name, str):
                return
            fn = group.file.filename
            var = posixpath.join(group.name, name).lstrip("/") if not name.startswith("/") else name.lstrip("/")
            if _under_output(fn) and _is_sink(fn, var):
                _MIRRORS[(_rel(fn), var)] = None
                _MASKS.pop((_rel(fn), var), None)
                _commit({"event": "write_unrecorded", "lib": "h5py.link", "path": os.path.realpath(fn),
                         "rel": _rel(fn), "var": var})
        except Exception:  # noqa: BLE001
            T._count("internal_error")

    delitem = h5py.Group.__delitem__

    def h5_delitem(self, name):
        r = delitem(self, name)
        _replaced(self, name)
        return r
    h5py.Group.__delitem__ = h5_delitem

    move = h5py.Group.move

    def h5_move(self, source, dest):
        r = move(self, source, dest)
        _replaced(self, source)            # the sink moved away: whatever takes its name is unseen
        _replaced(self, dest)
        return r
    h5py.Group.move = h5_move

    copy = h5py.Group.copy

    def h5_copy(self, source, dest, *a, **k):
        r = copy(self, source, dest, *a, **k)
        if isinstance(dest, str):
            _replaced(self, dest)
        elif isinstance(dest, h5py.Group):
            nm = k.get("name") or (a[0] if a else None) or (source if isinstance(source, str)
                                                            else getattr(source, "name", None))
            if isinstance(nm, str):
                _replaced(dest, posixpath.basename(nm))
        return r
    h5py.Group.copy = h5_copy

    gsetitem = h5py.Group.__setitem__

    def h5_gsetitem(self, name, obj):
        """h["mhw"] = array creates the variable from the array (a write with its
        provenance); h["mhw"] = <dataset or link> links values the hooks never saw."""
        if T._STATE is None or not _under_output(self.file.filename):
            return gsetitem(self, name, obj)
        nm = name.decode("utf-8", "replace") if isinstance(name, bytes) else name
        linked = isinstance(obj, (h5py.Dataset, h5py.Group, h5py.Datatype, h5py.SoftLink,
                                  h5py.ExternalLink, h5py.HardLink)) or not isinstance(nm, str)
        var = posixpath.join(self.name, nm).lstrip("/") if isinstance(nm, str) and not nm.startswith("/") \
            else (nm.lstrip("/") if isinstance(nm, str) else "")
        if linked or not _is_sink(self.file.filename, var):
            r = gsetitem(self, name, obj)
            if linked:
                _replaced(self, nm)
            return r
        rec, _, o2 = _sink_begin("h5py.setlink", self.file.filename, var, Ellipsis, obj)
        r = gsetitem(self, name, o2)
        try:
            d = self[nm]
            _mirror(rec, self.file.filename, var, Ellipsis, o2, full=True, dtype=d.dtype,
                    var_shape=d.shape, repr_="raw")
            _commit(rec)
        except Exception:  # noqa: BLE001
            T._count("internal_error")
        return r
    h5py.Group.__setitem__ = h5_gsetitem

    resize = h5py.Dataset.resize

    @T._timed
    def _resized(self, old):
        try:
            new = tuple(self.shape)
            fn = self.file.filename
            var = _h5_var(self)
            if T._STATE is not None and _under_output(fn) and _is_sink(fn, var) and new != old:
                k = (_rel(fn), var)
                m = _MIRRORS.get(k)
                if any(b < a for a, b in zip(old, new)) or m is None or len(new) != len(old):
                    # shrinking destroys values: nothing recorded before survives
                    _MIRRORS[k] = None
                    _commit({"event": "write_unrecorded", "lib": "h5py.resize", "path": os.path.realpath(fn),
                             "rel": _rel(fn), "var": var})
                else:                       # growth keeps values; new elements hold the fill
                    g = np.full(new, self.fillvalue if self.fillvalue is not None else 0, m.dtype)
                    g[tuple(slice(0, n) for n in m.shape)] = m
                    _MIRRORS[k] = g
        except Exception:  # noqa: BLE001
            T._count("internal_error")

    def h5_resize(self, size, axis=None):
        old = tuple(self.shape)
        r = resize(self, size, axis)
        _resized(self, old)
        return r
    h5py.Dataset.resize = h5_resize

    write_direct = h5py.Dataset.write_direct

    def h5_write_direct(self, source, source_sel=None, dest_sel=None):
        r = write_direct(self, T._unwrap(source) if isinstance(source, T.TArray) else source,
                         source_sel, dest_sel)
        try:                                # not modelled: the variable's provenance is cleared
            if T._STATE is not None and _under_output(self.file.filename):
                kt = T._collect(source, [])
                if kt:
                    T._escape_prov(P.union([t._p for t in kt], 0), "write_direct")
                _replaced(self.file, "/" + _h5_var(self))
        except Exception:  # noqa: BLE001
            T._count("internal_error")
        return r
    h5py.Dataset.write_direct = h5_write_direct


# --------------------------------------------------------------- netCDF4

def _patch_netcdf4():
    import netCDF4

    ds_init = netCDF4.Dataset.__init__

    def init(self, filename, mode="r", *a, **k):
        ds_init(self, filename, mode, *a, **k)
        try:
            if k.get("memory") is not None:
                _mem_ds[id(self)] = (_content_ident(k["memory"]) or _bytes_ident(k["memory"])
                                     or "mem:netCDF4:" + str(filename))
            else:
                _mem_ds.pop(id(self), None)
                if T._STATE is not None and (not str(mode).startswith("r") or "+" in str(mode)):
                    _note_write_open(filename)
            if mode in ("w", "x") and _under_output(os.fspath(filename)):
                _sink_event("open_w", os.fspath(filename))
        except Exception:  # noqa: BLE001
            T._count("internal_error")
    try:
        netCDF4.Dataset.__init__ = _data_call(
            "open", "netCDF4.Dataset",
            lambda a, k: (_local(a[1] if len(a) > 1 else k.get("filename")),) * 2, init,
            write=lambda a, k: not str(a[2] if len(a) > 2 else k.get("mode", "r")).startswith("r")
            or str(a[2] if len(a) > 2 else k.get("mode", "r")).startswith("r+"))
    except TypeError:
        T._count("netcdf4_init_unpatched")

    def ident(var) -> str:
        g = var.group()
        while getattr(g, "parent", None) is not None:
            g = g.parent
        if id(g) in _mem_ds:
            return _mem_ds[id(g)]
        try:
            return _ident_for_path(g.filepath())
        except ValueError:
            return "mem:netCDF4"

    getitem = netCDF4.Variable.__getitem__

    def nc_getitem(self, elem):
        r = getitem(self, elem)
        if T._STATE is None:
            return r
        try:
            fp = self.group().filepath()
            if _is_out(fp) and not getattr(_tl, "xr_write", False):
                _reread(fp)
        except ValueError:
            pass                           # in-memory dataset
        except Exception:  # noqa: BLE001
            T._count("internal_error")
        if self.name == T.VAR:
            return T.ledger("netCDF4", ident(self), self.shape, elem, r)
        try:
            fp = self.group().filepath()
        except ValueError:                 # an in-memory dataset: its bytes named nothing here
            return r
        return _other_variable(r, fp)
    netCDF4.Variable.__getitem__ = _data_call("read", "netCDF4.Variable.__getitem__", _nc_target, nc_getitem)

    setitem = netCDF4.Variable.__setitem__

    def nc_setitem(self, elem, data):
        if T._STATE is None:
            return setitem(self, elem, data)
        out = False
        try:
            fp = self.group().filepath()
            out = _under_output(fp)
        except ValueError:
            pass                           # an in-memory dataset has no file path
        except Exception:  # noqa: BLE001
            T._count("internal_error")
        if not out:
            return setitem(self, elem, data)
        rec, e2, d2 = _sink_begin("netCDF4", fp, self.name, elem, data,
                                  fill_rule=lambda v, m, var=self: _nc_filled(var, v, m))
        rec = None if getattr(_tl, "xr_write", False) else rec
        r = setitem(self, e2, d2)
        if rec is not None:
            try:
                packed = bool({"scale_factor", "add_offset"} & set(self.ncattrs()))
            except Exception:  # noqa: BLE001
                packed = True
            _mirror(rec, fp, self.name, e2, d2, var_shape=self.shape, orthogonal=True,
                    dtype=None if packed else self.dtype, repr_="decoded" if packed else "raw")
        _commit(rec)
        return r
    netCDF4.Variable.__setitem__ = nc_setitem


# --------------------------------------------------------------- sinks

def _nc_filled(var, data, mask):
    """What netCDF4's Variable.__setitem__ stores for a masked value (its own rule, from
    netCDF4/_netCDF4.pyx): the data where the masked data already equal a scalar
    missing_value; otherwise the masked elements become missing_value, else _FillValue,
    else the default fill of the type. Returns (stored values, positions stored as fill)."""
    import netCDF4
    attrs = set(var.ncattrs())
    if "missing_value" in attrs and np.all(np.isin(data[mask], np.atleast_1d(var.missing_value))):
        return data, None
    if "missing_value" in attrs:
        fill = np.asarray(var.missing_value)
        if fill.shape != ():
            raise ValueError("vector missing_value")
    elif "_FillValue" in attrs:
        fill = var._FillValue
    else:
        fill = netCDF4.default_fillvals[var.dtype.str[1:]]
    out = np.array(data, copy=True)
    out[mask] = fill
    return out, mask


def _patch_masked():
    """MaskedArray provenance (tracer: `_p` in the masked array's dict) kept current:
    numpy functions on masked arrays go through the models; numpy's attribute copying
    between masked arrays (`_update_from`) never propagates a parent's provenance; the
    in-place methods that write the buffer without a TArray view are hooked."""
    MA = np.ma.MaskedArray
    nd_af = np.ndarray.__array_function__
    agnostic = {"stack", "concatenate", "vstack", "hstack", "dstack", "column_stack", "append",
                "expand_dims", "transpose", "moveaxis", "swapaxes", "reshape", "ravel", "squeeze",
                "atleast_1d", "atleast_2d", "atleast_3d", "broadcast_to", "flip", "flipud", "fliplr",
                "roll", "take", "repeat", "copy"}

    def any_mask(x):
        if isinstance(x, MA):
            m = x.__dict__.get("_mask", np.ma.nomask)
            return m is not np.ma.nomask and bool(np.any(np.ndarray.view(np.asarray(m), np.ndarray)))
        if isinstance(x, (list, tuple)):
            return any(any_mask(v) for v in x)
        if isinstance(x, dict):
            return any(any_mask(v) for v in x.values())
        return False

    def ma_array_function(self, func, types, args, kwargs):
        def call():
            return nd_af(self, func, types, args, kwargs)
        if T._STATE is None:
            return call()
        name = getattr(func, "__name__", "")
        if name in agnostic or not (any_mask(args) or any_mask(kwargs)):
            return T._function(func, args, kwargs, call=call)
        # A real mask changes which values combine: keep what the internals computed
        # (their operations are modelled); if they produced no provenance, upper bound only.
        r = call()
        tracked = T._collect((args, kwargs), [])
        if tracked and isinstance(r, np.ndarray) and T._prov(r) is None:
            return T._generic(r, tracked)
        return r
    MA.__array_function__ = ma_array_function

    ma_reduce = MA.__reduce__

    def reduce(self):
        # Pickling names the array's base class, and TArray names itself numpy.ndarray, so pickle refuses it: a masked
        # array read through netCDF4 could not be returned by a multiprocessing worker, in traced runs only. What is
        # pickled is plain data, and it leaves tracking (the units stay on record, as for a TArray).
        func, args, state = ma_reduce(self)
        args = tuple(np.ndarray if a is T.TArray else a for a in args)
        p = T._ma_prov(self) if T._STATE is not None else None
        if p is None or p.is_empty():
            return func, args, state
        travel = T._prov_for_pickle(p)
        if travel is None:
            T._escape_prov(p, "pickle")
            return func, args, state
        return T._rebuild_masked, ((func, args, state), *travel)
    MA.__reduce__ = reduce

    update_from = MA._update_from

    def ma_update_from(self, obj):
        keep = T._ma_prov(self) if isinstance(obj, MA) else None
        update_from(self, obj)
        if T._STATE is None:
            return
        try:
            d = self.__dict__
            for k in ("_optinfo", "_basedict"):
                o = d.get(k)
                if isinstance(o, dict):
                    o.pop("_p", None)          # never inherited by later views
            if isinstance(obj, MA):
                parent = T._ma_prov(obj)
                if keep is not None:
                    T._set_ma_prov(self, keep)  # this array's own, from its data, not the parent's
                elif parent is not None:
                    # made from a tracked parent by code with no model (a C method on the
                    # masked array): upper bound only, never a lower one
                    T._set_ma_prov(self, P.hi_only(parent, self.ndim))
                else:
                    d.pop("_p", None)
            elif isinstance(obj, T.TArray):
                same = T._same_elements(np.ndarray.view(self, np.ndarray), T._plain(obj))
                T._set_ma_prov(self, obj._p if same else P.hi_only(obj._p, self.ndim))
            else:
                d.pop("_p", None)
        except Exception:  # noqa: BLE001
            T._count("internal_error")
    MA._update_from = ma_update_from

    def mutator(name, constant=False):
        orig = getattr(MA, name)

        def wrapped(self, *a, **k):
            r = orig(self, *a, **k)
            if T._STATE is None:
                return r
            try:
                old = T._ma_prov(self)
                vp = T._prov(a[0]) if (constant and a) else None
                if constant:
                    new = P.Prov.none() if vp is None else P.hi_only(vp, self.ndim)
                elif old is not None:
                    new = P.hi_only(old, self.ndim)
                else:
                    return r
                T._set_ma_prov(self, new)
                T._invalidate(self, vp)
            except Exception:  # noqa: BLE001
                T._count("internal_error")
            return r
        wrapped.__name__ = name
        setattr(MA, name, wrapped)

    wrap = MA.__array_wrap__

    def array_wrap(self, obj, context=None, return_scalar=False):
        r = wrap(self, obj, context, return_scalar)
        if T._STATE is None or obj is not self or context is None:
            return r
        # A ufunc wrote into this masked array (out=) with no tracked operand of its own
        # type in charge: its old provenance no longer holds. The call's where= is not
        # visible here, so the lower bound is dropped and the upper bound keeps the old
        # values and the inputs. (With a tracked TArray operand, the TArray's own hook
        # runs after this and sets the exact provenance.)
        try:
            ins = T._collect(context[1], [])
            old = T._ma_prov(self)
            parts = ([old] if old is not None else []) + [t._p for t in ins]
            new = P.hi_only(P.union(parts, self.ndim), self.ndim) if parts else None
            if new is not None or old is not None:
                T._set_ma_prov(self, new if new is not None else P.Prov.none())
                T._invalidate(self, P.union([t._p for t in ins], self.ndim) if ins else None)
        except Exception:  # noqa: BLE001
            T._count("internal_error")
        return r
    MA.__array_wrap__ = array_wrap

    ma_view = MA.view

    def view(self, *a, **k):
        r = ma_view(self, *a, **k)
        if T._STATE is not None and isinstance(r, np.ndarray) and not isinstance(r, (MA, T.TArray)) \
                and T._ma_prov(self) is not None:
            # a plain view of a tracked masked array: writes through it are unseen
            try:
                T._escape_prov(T._ma_prov(self), "plain_view")
                T._invalidate(self, None, include_self=True)
            except Exception:  # noqa: BLE001
                T._count("internal_error")
        return r
    MA.view = view

    # In-place attribute writes (Codex on bf0cdec). A masked array is not a TArray, so
    # numpy's setters would leave its provenance (`_p` in its dict) stale. The mask, a
    # TArray when it carries provenance, follows through TArray's own setters.
    nd_shape, nd_strides = np.ndarray.__dict__["shape"], np.ndarray.__dict__["strides"]
    ma_shape, ma_dtype = MA.__dict__["shape"], MA.__dict__["dtype"]

    def set_shape(self, value):
        old_shape, old = nd_shape.__get__(self), T._ma_prov(self)
        ma_shape.fset(self, value)
        if T._STATE is None or old is None:
            return
        new_shape = nd_shape.__get__(self)
        # in C index order, without a copy, as for an ndarray (TArray.shape)
        T._set_ma_prov(self, T._try(lambda: P.reshape(old, old_shape, new_shape), old, len(new_shape)))
    MA.shape = property(ma_shape.fget, set_shape, doc=ma_shape.__doc__)

    def set_dtype(self, value):
        old_shape, old = nd_shape.__get__(self), T._ma_prov(self)
        ma_dtype.fset(self, value)
        if T._STATE is None or old is None:
            return
        if nd_shape.__get__(self) != old_shape:
            T._set_ma_prov(self, P.hi_only(old, self.ndim))
    MA.dtype = property(ma_dtype.fget, set_dtype, doc=ma_dtype.__doc__)

    def set_strides(self, value):
        nd_strides.__set__(self, value)
        if T._STATE is not None:
            T._remapped(self, "strides_set")
    MA.strides = property(nd_strides.__get__, set_strides)

    def unmasked(m) -> bool:
        k = m.__dict__.get("_mask", np.ma.nomask)
        return k is np.ma.nomask or not bool(np.any(np.ndarray.view(np.asarray(k), np.ndarray)))

    def positional(name):
        """Methods whose result has the same elements in the same positions (astype, copy)."""
        orig = getattr(MA, name)

        def wrapped(self, *a, **k):
            r = orig(self, *a, **k)
            if T._STATE is not None and isinstance(r, MA) and r.shape == self.shape:
                pp = T._ma_prov(self)
                if pp is not None:
                    T._set_ma_prov(r, pp)
            return r
        wrapped.__name__ = name
        setattr(MA, name, wrapped)

    for n in ("astype", "copy", "__copy__"):
        positional(n)

    def reduction(name):
        """Reductions along an axis. Exact when nothing is masked; with a real mask the
        masked elements do not take part, which the axis model cannot express: then the
        internals' provenance is kept (they go through filled(), modelled), else upper only."""
        orig = getattr(MA, name)

        def wrapped(self, *a, **k):
            r = orig(self, *a, **k)
            if T._STATE is None:
                return r
            pp = T._ma_prov(self)
            if pp is None:
                return r
            try:
                axis = k.get("axis", a[0] if a else None)
                keep = bool(k.get("keepdims", False))
                if unmasked(self):
                    red = P.reduce(pp, self.shape, axis, keep)
                    if isinstance(r, np.ndarray):
                        return T._wrap(r, red)
                    T._escape_prov(red, "scalar")
                    return r
                if isinstance(r, np.ndarray) and T._prov(r) is None:
                    return T._wrap(r, P.hi_only(pp, r.ndim))
                if not isinstance(r, np.ndarray):
                    T._escape_prov(pp, "scalar")
            except Exception:  # noqa: BLE001
                T._count("internal_error")
            return r
        wrapped.__name__ = name
        setattr(MA, name, wrapped)

    for n in ("sum", "mean", "prod", "min", "max", "std", "var", "any", "all", "argmin", "argmax", "ptp"):
        if n in MA.__dict__ or hasattr(MA, n):
            reduction(n)

    mutator("fill", constant=True)
    for n in ("partition", "byteswap", "setfield"):
        mutator(n)


@T._timed
def _sink_event(kind: str, path: str):
    if kind == "open_w":
        rel = _rel(path)
        for k in [k for k in _MIRRORS if k[0] == rel]:
            del _MIRRORS[k]
        for k in [k for k in _MASKS if k[0] == rel]:
            del _MASKS[k]
    st = T._STATE
    if st is not None:
        st._write("sinks", {"t": time.time(), "seq": _next_seq(), "event": kind,
                            "path": os.path.realpath(path), "rel": _rel(path)})


# NumPy names the sink path uses, captured at import: agent code that rebinds them
# later (np.ma.MaskedArray = ..., np.ndarray.copy = ...) cannot reach this path.
_NDARRAY = np.ndarray
_NDCOPY = np.ndarray.copy
_NDVIEW = np.ndarray.view
_GENERIC = np.generic
_SCALARS = (int, float, bool)
_MASKED = np.ma.MaskedArray
_NOMASK = np.ma.nomask
_NPBOOL = np.bool_
_GETPROFILE, _SETPROFILE = sys.getprofile, sys.setprofile
_GETTRACE, _SETTRACE = sys.gettrace, sys.settrace


def _normalize_key(key):
    """The key as an exact tuple, iterated once: the record and the library then see
    the same elements, whatever the agent's key object does when iterated."""
    if key is None or key is Ellipsis or type(key) is not tuple and not isinstance(key, tuple):
        return key
    return tuple(key)


@T._timed
def _sink_begin(lib: str, path, var: str, key, value, *, fill_rule=None):
    """Record one write under the output dir and return (rec, key, value) to hand to
    the library. No agent code runs between reading the value's provenance and
    copying it: the value is read first, by type identity against the names captured
    above, inline, with profiling and tracing paused; the key (which may run agent
    code when iterated) is normalised after. Anything but an exact numpy array or a
    scalar (a subclass, a masked array, an object with its own __array__) may run
    agent code when read, so its write is recorded as of unknown origin. For the sink
    variable the library gets the copy, so a callback of the write that changes the
    agent's array cannot change what is stored; a tracked key escapes (it selects what
    the output holds). Any other write keeps its tracked value, so its conversion
    stays an escape."""
    st = T._STATE
    sink = _is_sink(path, var)
    # Provenance and copy are taken with profiling and tracing paused, inline, so no
    # Python-level callback (sys.setprofile / settrace) can run between them.
    _gp, _gt = _GETPROFILE(), _GETTRACE()
    _SETPROFILE(None)
    _SETTRACE(None)
    try:
        t = type(value)
        exact = t is T.TArray or t is _NDARRAY or t is _MASKED or value is None or t in _SCALARS or (
            t.__module__ == "numpy" and issubclass(t, _GENERIC))
        vp = None
        write_mask = None
        if t is T.TArray or t is _MASKED:
            try:
                d = object.__getattribute__(value, "__dict__")
            except AttributeError:
                d = None
            if type(d) is dict and not any(type(k) is not str for k in dict.__iter__(d)):
                vp = dict.get(d, "_p")
                if t is _MASKED:
                    mk = dict.get(d, "_mask", _NOMASK)
                    if type(mk) is T.TArray or type(mk) is _NDARRAY:
                        write_mask = _NDCOPY(_NDVIEW(mk, _NDARRAY)).astype(bool)
                    elif mk is not _NOMASK and type(mk) is not _NPBOOL:
                        exact = False      # a mask that is not an array: unknown origin
            if P.STOPPED[0]:
                vp = P.Prov.none() if t is T.TArray else None    # what its record says was true when tracking stopped
            if t is _MASKED and vp is None:
                pass                       # an untracked masked value: certifies nothing, sound
            elif type(vp) is not P.Prov:
                vp, exact = None, False    # a tampered instance dict: certifies nothing
        if sink and exact and (t is T.TArray or t is _NDARRAY or t is _MASKED):
            out_value = _NDCOPY(_NDVIEW(value, _NDARRAY))       # the data, as stored bytes
        else:
            out_value = value
    finally:
        _SETPROFILE(_gp)
        _SETTRACE(_gt)
    rec = None
    try:
        vshape = list(np.shape(out_value)) if exact else None
        kn = _normalize_key(key)
        kt = T._collect(kn, []) if kn is not None else []
        if kt:
            T._escape_prov(P.union([t._p for t in kt], 0), "sink_key")
        out_key = T._unwrap(kn) if (sink and kn is not None) else kn
        stored_mask = None
        if sink and exact and write_mask is not None and write_mask.any():
            if fill_rule is None:
                stored_mask = None         # the library stores the data under the mask (h5py)
            else:
                out_value, stored_mask = fill_rule(out_value, write_mask)
        if st is not None:
            rec = {"event": "write", "lib": lib, "path": os.path.realpath(path), "rel": _rel(path),
                   "var": var, "value_shape": vshape if vshape is not None else list(np.shape(value)),
                   "key": _key_repr(kn if kn is not None else Ellipsis),
                   "tracked": vp is not None and not vp.is_empty()}
            if vp is not None and not vp.is_empty():
                rec["prov"] = st.save_prov(vp, "sink")
            if stored_mask is not None:
                rec["_write_mask"] = stored_mask      # positions stored as fill (in the value)
        return rec, out_key, out_value
    except Exception:  # noqa: BLE001
        T._count("internal_error")
        bad = None if st is None else {"event": "write_unrecorded", "lib": lib,
                                       "path": os.path.realpath(path), "rel": _rel(path), "var": var}
        return bad, key, out_value


@T._timed
def _h5_var(dset) -> str:
    """The variable a h5py dataset is, by object identity: a hard link (or any other
    name) of the sink dataset resolves to the sink's name."""
    name = (dset.name or "").lstrip("/")
    try:
        fn = dset.file.filename
        if _is_sink(fn, name):
            return name
        f = dset.file
        for var in config.sink_spec().get(_rel(fn) or "", ()):
            if var in f and f[var] == dset:
                return var
    except Exception:  # noqa: BLE001
        T._count("internal_error")
    return name


def _is_sink(path, var: str) -> bool:
    """Whether `var` of the output file at `path` is the scientific sink (config.SINKS).
    Only its writes are covered by the sink record; a value written anywhere else in
    the output directory may be read back, so its conversion stays an escape."""
    rel = _rel(path)
    return rel is not None and var.lstrip("/") in config.sink_spec().get(rel, ())


def _rel(path) -> str | None:
    st = T._STATE
    try:
        return str(Path(os.path.realpath(path)).relative_to(st.out))
    except (TypeError, ValueError, AttributeError):
        return None


_next_seq = T.next_seq


@T._timed
def _sink_write(lib: str, path: str, var: str, var_shape, key, value):
    """Prepare the record of one write of `value` into variable `var` of an output file,
    with the value's provenance as it is now. Nothing is recorded until `_commit(rec)`,
    called after the write succeeded: a failed write certifies nothing."""
    st = T._STATE
    if st is None:
        return None
    try:
        p = T._prov(value)
        vshape = list(np.shape(value))
        rec = {"event": "write", "lib": lib,
               "path": os.path.realpath(path), "rel": _rel(path), "var": var, "value_shape": vshape,
               "key": _key_repr(key), "tracked": p is not None and not p.is_empty()}
        if p is not None and not p.is_empty():
            rec["prov"] = st.save_prov(p, "sink")
        return rec
    except Exception:  # noqa: BLE001
        st.count("internal_error")
        return {"event": "write_unrecorded", "lib": lib, "path": os.path.realpath(path),
                "rel": _rel(path), "var": var}


# In-memory mirror of each sink variable's content, built from the recorded writes
# with the write's own indexing. Each committed write carries a checksum of the
# mirror after it; analyse.py compares the last one with the final file content.
# Any write the hooks did not see (a delete and re-create, h5py move or copy,
# low-level writes, another process, a dump that failed half-way) makes them differ,
# and the run cannot be certified (never a false complete).
_MIRRORS: dict[tuple[str, str], np.ndarray | None] = {}


def content_crc(a) -> int:
    """Checksum of values as float64, NaNs canonical (shared with analyse.py)."""
    x = np.array(np.ma.getdata(a), dtype="f8", copy=True)
    x[np.isnan(x)] = np.nan
    x[x == 0] = 0.0                    # -0.0 and +0.0 store alike in integer variables
    return zlib.crc32(np.ascontiguousarray(x).tobytes()) ^ zlib.crc32(repr(x.shape).encode())


def cf_decoded(raw, attrs) -> np.ndarray:
    """Stored values decoded as CF readers (xarray, netCDF4) do: fill and missing values
    to NaN, then scale_factor and add_offset. The mirror may hold either form."""
    x = np.array(raw, dtype="f8", copy=True)
    for k in ("_FillValue", "missing_value"):
        if k in attrs:
            for v in np.atleast_1d(np.asarray(attrs[k], dtype="f8")):
                x[x == v] = np.nan
    if "scale_factor" in attrs:
        x = x * float(np.asarray(attrs["scale_factor"]).reshape(-1)[0])
    if "add_offset" in attrs:
        x = x + float(np.asarray(attrs["add_offset"]).reshape(-1)[0])
    return x


_MASKS: dict = {}                     # (rel, var) -> bool array: positions stored as fill


def _track_masked(rec, k, kk, full, var_shape, shape):
    """Positions of the variable that hold a fill value written for a masked element.
    Their recorded provenance does not hold (analyse.py checks they are outside R)."""
    wm = rec.pop("_write_mask", None)
    mm = _MASKS.get(k)
    if wm is None and mm is None:
        return
    if full:
        mm = (np.broadcast_to(wm, shape).copy() if wm is not None else np.zeros(shape, bool))
    else:
        if mm is None:
            mm = np.zeros(var_shape, bool)
        if tuple(mm.shape) != tuple(var_shape):
            g = np.zeros(var_shape, bool)
            g[tuple(slice(0, n) for n in mm.shape)] = mm
            mm = g
        np.ndarray.__setitem__(mm, kk, wm if wm is not None else False)
    _MASKS[k] = mm
    rec["masked_shape"] = list(mm.shape)
    rec["masked"] = T._rle(np.flatnonzero(mm))


@T._timed
def _mirror(rec, path, var, key, value, *, var_shape=None, full=False, dtype=None, orthogonal=False,
            repr_="raw"):
    """Apply one recorded write to the mirror of a sink variable. `dtype`: the stored
    type, for raw writes (the value is cast as the library casts it); None where the
    library decodes (CF packing), in which case the file is compared decoded."""
    if rec is None or T._STATE is None or not _is_sink(path, var):
        return
    k = (_rel(path), var)
    try:
        v = np.array(T._unwrap(np.ma.getdata(value)) if value is not None else None, copy=True)
        v = np.ndarray.view(v, np.ndarray) if isinstance(v, np.ndarray) else v
        if dtype is not None:
            v = v.astype(dtype)
        m = _MIRRORS.get(k)
        if full:
            if var_shape is not None and tuple(v.shape) != tuple(var_shape):
                v = (v.reshape(var_shape) if v.size == int(np.prod(var_shape))
                     else np.broadcast_to(v, var_shape)).copy()
            m = v
        else:
            if m is None and var_shape is not None:
                # first write seen to this variable: unwritten elements hold the fill,
                # which only matters if they stay unwritten (then the check fails: unknown)
                m = np.zeros(var_shape, v.dtype if v.dtype.kind in "biuf" else "f8")
            if m is None:
                raise ValueError("no mirror")
            if var_shape is not None and tuple(m.shape) != tuple(var_shape):
                if len(var_shape) != m.ndim or any(a < b for a, b in zip(var_shape, m.shape)):
                    raise ValueError("variable shape changed")
                g = np.zeros(var_shape, m.dtype)             # netCDF4 unlimited dimension grew
                g[tuple(slice(0, n) for n in m.shape)] = m
                m = g
            kk = T._unwrap(key)
            if orthogonal and isinstance(kk, tuple) and sum(np.ndim(x) > 0 for x in kk) > 1:
                raise ValueError("orthogonal indexing")
            np.ndarray.__setitem__(m, kk, v)
        _track_masked(rec, k, None if full else T._unwrap(key), full, var_shape, m.shape)
        _MIRRORS[k] = m
        rec["mirror_crc"] = content_crc(m)
        rec["mirror_repr"] = repr_          # compared with the file in this representation only
    except Exception:  # noqa: BLE001
        _MIRRORS[k] = None
        _MASKS.pop(k, None)
        rec.pop("_write_mask", None)
        rec["mirror_crc"] = None


def _covers_all(key) -> bool:
    keys = key if isinstance(key, tuple) else (key,)
    return all(k is Ellipsis or (isinstance(k, slice) and k == slice(None)) for k in keys)


@T._timed
def _commit(*recs):
    st = T._STATE
    if st is None:
        return
    for rec in recs:
        if rec is not None:
            try:
                rec.pop("_write_mask", None)
                st._write("sinks", dict(rec, t=time.time(), seq=_next_seq()))
            except Exception:  # noqa: BLE001
                st.count("internal_error")


@T._timed
def _reread(path: str):
    """A data read from a file under the output directory: values come back untracked.
    Recorded once per process; from then on every sink write is suspect (analyse.py)."""
    if getattr(_reread, "done", False):
        return
    _reread.done = True
    _sink_event("reread", path)


_OUT_CACHE: dict[str, bool] = {}


def _is_out(path) -> bool:
    k = os.path.abspath(str(path))
    v = _OUT_CACHE.get(k)
    if v is None:
        v = _OUT_CACHE[k] = _under_output(k)
    return v


def _key_repr(key):
    if key is Ellipsis:
        return "..."
    if not isinstance(key, tuple):
        key = (key,)
    out = []
    for k in key:
        if k is Ellipsis:
            out.append("...")
        elif isinstance(k, slice):
            out.append(["slice", k.start, k.stop, k.step])
        elif isinstance(k, (int, np.integer)):
            out.append(int(k))
        elif k is None:
            out.append(None)
        else:
            a = np.asarray(T._unwrap(k))
            out.append(["bool" if a.dtype == bool else "list", T._rle(np.nonzero(a)[0] if a.dtype == bool else a)])
    return out


def _patch_xarray():
    import xarray.backends.writers as W

    dump = W.dump_to_store

    def dump_to_store(dataset, store, *a, **k):
        path = getattr(store, "_filename", None) or getattr(getattr(store, "ds", None), "filepath", lambda: None)()
        lazy, recs, mirrored = [], [], []
        if T._STATE is not None and path and _under_output(str(path)):
            try:
                _sink_event("open_w", str(path)) if getattr(store, "_mode", "w") == "w" else None
                for name, v in dataset.data_vars.items():
                    data = v.variable._data
                    if not isinstance(data, np.ndarray) and hasattr(data, "compute"):
                        lazy.append(name)
                        continue
                    val = data if isinstance(data, np.ndarray) else np.asarray(data)
                    rec, _, snap = _sink_begin("xarray", str(path), str(name), Ellipsis, val)
                    recs.append(rec)
                    # the mirror is built from the snapshot taken with the record: if the
                    # values change before the store writes them, the check fails
                    mirrored.append((str(name), snap))
            except Exception:  # noqa: BLE001
                T._count("internal_error")
        # Low-level hooks record only variables that were lazy here (dask).
        _tl.xr_write = not lazy
        try:
            # The low-level hooks hand the library a copy for the sink variable only
            # (_sink_begin), so other variables' conversions stay escapes.
            r = dump(dataset, store, *a, **k)
        except BaseException:
            # Part of the dump may be on disk: its variables' content is unknown.
            _commit(*[dict(x, event="write_unrecorded") for x in recs if x is not None])
            raise
        finally:
            _tl.xr_write = False
        for x, (name, val) in zip(recs, mirrored):
            _mirror(x, str(path), name, Ellipsis, val, full=True, repr_="decoded")
        _commit(*recs)                     # only once the dump succeeded
        return r
    W.dump_to_store = dump_to_store

    # A coordinate's values, in the agent's hands: as a coordinate read from a file directly (_other_variable).
    from xarray import DataArray, IndexVariable, Variable

    # xarray converts dates and objects only for exactly numpy's type (`type(data) is np.ndarray`): a tracked array would keep
    # datetime64[D] where the same code untraced has datetime64[s]. It gets numpy's type for that, and its record back.
    from xarray.core import variable as xr_variable
    compatible = xr_variable.as_compatible_data

    def as_compatible_data(data, fastpath=False):
        if fastpath or not isinstance(data, T.TArray) or data.dtype.kind not in "OMm":
            return compatible(data, fastpath=fastpath)
        p = data._p
        r = compatible(T._plain(data), fastpath=fastpath)
        return T._wrap(r, p) if type(r) is np.ndarray and r.shape == data.shape else r
    for m in list(sys.modules.values()):
        if getattr(m, "__name__", "").startswith("xarray") and getattr(m, "as_compatible_data", None) is compatible:
            m.as_compatible_data = as_compatible_data

    def wrap_index_values(cls, is_index):
        prop = cls.__dict__["values"]

        def values(self):
            r = prop.fget(self)
            if T._STATE is not None and type(r) is np.ndarray and r.ndim and is_index(self) and T._is_agent_frame(2):
                return _made(r)
            return r
        setattr(cls, "values", property(values, prop.fset, prop.fdel, prop.__doc__))
    wrap_index_values(DataArray, lambda da: isinstance(da.variable, IndexVariable))
    wrap_index_values(Variable, lambda v: isinstance(v, IndexVariable))


# --------------------------------------------------------------- numpy

_KEEP_PREFIX = ("xarray", "dask", "icsa.instruments", "numpy")


def _keeps(depth=3) -> bool:
    if T._is_agent_frame(depth):
        return True
    mod = T._caller_module(depth)
    return mod.startswith(_KEEP_PREFIX)


def _has_tracked(obj) -> bool:
    if isinstance(obj, T.TArray):
        return not obj._p.is_empty()
    if isinstance(obj, np.ma.MaskedArray):
        return isinstance(obj._data, T.TArray)
    if isinstance(obj, T._TSCALARS):
        return not obj._p.is_empty()
    if type(obj) in (list, tuple):
        return _seq_tracked(obj, 0)
    return False


def _seq_tracked(seq, depth: int) -> bool:
    """Whether a list holds an array the conversion would strip silently, wherever it sits. A tracked scalar counts at the
    top level only: below that its units are already on record as an escape, and a nested comprehension over cells has
    too many to model."""
    for v in seq:
        t = type(v)
        if t in _PLAIN_TYPES:
            continue
        if t is T.TArray or isinstance(v, np.ma.MaskedArray):
            return True
        if depth == 0 and isinstance(v, T._TSCALARS):
            return True
        if t in (list, tuple) and depth < 8 and _seq_tracked(v, depth + 1):
            return True
    return False


def _list_prov(obj, result_shape):
    """np.array(list of equal-shape tracked arrays): stack their provenance."""
    parts, shapes = [], []
    for v in obj:
        s = np.shape(v)
        p = _list_prov(v, s) if type(v) in (list, tuple) else T._prov(v)
        parts.append(P.reshape(p, s, (1,) + s) if p is not None else P.Prov.none())
        shapes.append((1,) + s)
    if len({s for s in shapes}) != 1 or (len(obj),) + shapes[0][1:] != tuple(result_shape):
        raise P._Unsupported
    return P.concatenate(parts, shapes, 0)


# Values that can hold no tracked array: a conversion of these needs no look inside them.
_PLAIN_TYPES = frozenset((np.ndarray, int, float, bool, complex, str, bytes, type(None), np.float64, np.float32,
                          np.int64, np.int32, np.int8, np.uint8, np.bool_))


_NO_ARG = object()
# numpy functions that take array-likes and do not dispatch on what is inside a list. Those that do (stack, concatenate, ...)
# keep the model they have, and must not be converted: their lists may not be one array. tests/instruments/test_batch_silent_loss.py
# calls every public function at the pinned numpy, so a function missing from here fails it.
_LIST_ARGS = ("allclose", "append", "array_equal", "array_equiv", "array_split", "delete", "dot", "geomspace",
              "histogram_bin_edges", "inner", "isclose", "kron", "linspace", "logspace", "outer", "polyder", "polyint", "polyval",
              "union1d",
              "all", "amax", "amin", "angle", "any", "argmax", "argmin", "argpartition", "argsort", "argwhere", "around",
              "atleast_1d", "atleast_2d", "atleast_3d", "average", "broadcast_to", "clip", "compress", "copy", "count_nonzero",
              "cumprod", "cumsum", "diagflat", "diagonal", "diff", "digitize", "ediff1d", "expand_dims", "extract", "fix",
              "flatnonzero", "flip", "fliplr", "flipud", "gradient", "histogram", "imag", "interp", "isin", "iscomplex",
              "isneginf", "isposinf", "isreal", "matrix_transpose", "max", "mean", "median", "min", "moveaxis",
              "nan_to_num", "nanargmax", "nanargmin", "nancumprod", "nancumsum", "nanmax", "nanmean", "nanmedian", "nanmin",
              "nanpercentile", "nanprod", "nanquantile", "nanstd", "nansum", "nanvar", "nonzero", "pad", "partition",
              "percentile", "permute_dims", "prod", "ptp", "quantile", "ravel", "real", "repeat", "require", "reshape",
              "resize", "roll", "rot90", "round", "searchsorted", "sort", "sort_complex", "squeeze", "std", "sum", "swapaxes",
              "take", "take_along_axis", "tile", "trace", "transpose", "trapezoid", "tril", "triu", "unique", "unwrap", "var",
              "where")
# These treat a list otherwise than as an array (np.split(list, 2) raises): converting it would change what the agent
# sees, so numpy answers as it does, and the units go on record.
_LIST_ESCAPES = ("split", "vsplit", "dsplit")
# Arrays numpy makes for the agent's code answer as the tracked type: a write of tracked values into one is seen. Science's rule
# (#2, 12:30Z): this stays only if it halves plain_operand and adds under 10% to median tool time. False takes it out, in one line.
MADE_ARRAYS = True
_MADE_KINDS = frozenset("biufc")    # dates, objects and text hold no data's values, and xarray converts them only for numpy's own type


def _made(r):
    return T._wrap(r, P.Prov.none()) if MADE_ARRAYS and r.dtype.kind in _MADE_KINDS else r
_MAKERS = ("zeros_like", "ones_like", "empty_like", "full_like", "arange", "linspace", "logspace", "geomspace", "eye", "identity",
           "indices", "meshgrid", "tri", "diag", "fromfunction", "fromiter", "copy", "outer", "broadcast_to", "tile", "repeat")


def _patch_numpy():
    orig = {n: getattr(np, n) for n in ("array", "asarray", "asanyarray", "ascontiguousarray",
                                        "asfortranarray", "empty", "zeros", "ones", "full",
                                        "frombuffer", "fromfile")}

    def make_conv(name):
        f = orig[name]
        first = "object" if name == "array" else "a"     # the first parameter's name: numpy takes it by keyword too

        def conv(obj=_NO_ARG, /, *a, **k):
            if obj is _NO_ARG:
                if first not in k:
                    return f(*a, **k)       # numpy's own error
                obj = k.pop(first)
            t = type(obj)
            if t in _PLAIN_TYPES and t is not np.ndarray:   # numpy's own loops call this millions of times
                return f(obj, *a, **k)
            if t is np.ndarray:
                r = f(obj, *a, **k)
                if r is not obj and type(r) is np.ndarray and T._STATE is not None and T._is_agent_frame(2):
                    return _made(r)
                return r
            if not _has_tracked(obj):
                if (T._STATE is not None and name in ("asarray", "asanyarray", "array")
                        and type(obj).__module__.startswith("xarray.") and hasattr(obj, "__array__")
                        and not a and not k and _keeps()):
                    # xarray's lazy wrappers: their __array__ yields our array, which the
                    # C-level conversion would strip. Same values, provenance kept.
                    # Decided before the call, never after a failure: running a read again
                    # would give the agent a retry it never asked for.
                    try:
                        inspect.signature(type(obj).__array__).bind(obj)
                    except (TypeError, ValueError):
                        return f(obj)
                    r = obj.__array__()
                    if isinstance(r, T.TArray):
                        return r.copy() if name == "array" else r
                    return f(r)
                r = f(obj, *a, **k)
                # a new array numpy made for the agent's code: writes into it are seen, and it is no plain operand
                if r is not obj and type(r) is np.ndarray and r.ndim and T._STATE is not None and T._is_agent_frame(2):
                    return _made(r)
                return r
            r = f(T._unwrap(obj) if isinstance(obj, (list, tuple, *T._TSCALARS)) else obj, *a, **k)
            if not _keeps():
                T._escape_prov(_any_prov(obj, np.ndim(r)), "foreign:" + T._caller_module(2))
                plain = T._plain(r) if type(r) is T.TArray else r
                if isinstance(plain, np.ndarray):
                    # The library holds a plain alias of a tracked buffer: writes through it
                    # are invisible, so no alias keeps its lo (never a false complete).
                    for t in T._collect(obj, []):
                        if isinstance(t, T.TArray) and np.may_share_memory(plain, T._plain(t)):
                            T._invalidate(t, None, include_self=True)
                            T._count("foreign_alias")
                return plain
            if isinstance(r, np.ma.MaskedArray):
                return r
            try:
                if isinstance(obj, (T.TArray, np.ma.MaskedArray, *T._TSCALARS)):
                    p = T._prov(obj)
                    p = p if np.shape(r) == np.shape(obj) else P.reshape(p, np.shape(obj), np.shape(r))
                else:
                    p = _list_prov(obj, np.shape(r))
            except Exception:  # noqa: BLE001
                T._count("unmodelled")
                p = P.hi_only(_any_prov(obj, np.ndim(r)), np.ndim(r))
            if isinstance(r, np.ndarray):
                return T._wrap(r, p) if type(r) is np.ndarray or type(r) is T.TArray else r
            return r
        conv.__name__ = f.__name__
        conv.__doc__ = f.__doc__
        conv.__wrapped__ = f
        return conv

    for n in ("array", "asarray", "asanyarray", "ascontiguousarray", "asfortranarray"):
        setattr(np, n, make_conv(n))

    def make_ctor(name):
        f = orig[name]

        def ctor(*a, **k):
            r = f(*a, **k)
            if T._STATE is None or type(r) is not np.ndarray:
                return r
            if name == "full":
                # numpy converts the fill value before copying it, so the array protocols never see it
                fill = a[1] if len(a) > 1 else k.get("fill_value")
                fp = T._prov(fill)
                if fp is not None and not fp.is_empty():
                    if _keeps():
                        return T._wrap(r, T._try(lambda: P.broadcast(fp, np.shape(fill), np.shape(r)), fp, r.ndim))
                    T._escape_prov(fp, "foreign:" + T._caller_module(2))
                    return r
            if T._is_agent_frame(2):
                return T._wrap(r, P.Prov.none()) if r.dtype.kind in _MADE_KINDS else r
            return r
        ctor.__name__ = f.__name__
        ctor.__doc__ = f.__doc__
        ctor.__wrapped__ = f
        return ctor

    for n in ("empty", "zeros", "ones", "full"):
        setattr(np, n, make_ctor(n))

    def make_decode(name):
        f = orig[name]

        def dec(*a, **k):
            r = f(*a, **k)
            if T._STATE is None:
                return r
            try:
                # frombuffer over a tracked array: the result aliases its buffer, and
                # writes through it are invisible, so no alias keeps its lo.
                src = a[0] if a else k.get("buffer")
                if isinstance(src, np.ndarray) and isinstance(r, np.ndarray) \
                        and np.may_share_memory(r, T._plain(src) if isinstance(src, T.TArray) else src):
                    T._raw_buffer(src, "frombuffer_alias")
            except Exception:  # noqa: BLE001
                T._count("internal_error")
            if T._is_agent_frame(2) and np.size(r) >= 1024:
                T._STATE._write("events", {"t": time.time(), "kind": "flag", "how": "raw_decode:" + name,
                                           "size": int(np.size(r))})
            return r
        dec.__name__ = f.__name__
        dec.__doc__ = f.__doc__
        dec.__wrapped__ = f
        return dec

    for n in ("frombuffer", "fromfile"):
        setattr(np, n, make_decode(n))

    # A tracked array in a Python list handed to numpy: dispatch does not look inside a list, and the C conversion strips
    # the array with no hook, so np.mean([a, b], axis=0) lost both silently: a false omitting on a common idiom. The list
    # goes through the tracked np.array first, as np.array(list) always has. ufuncs cannot be wrapped by name (np.add.reduce
    # must stay): np.sqrt(list) gives a plain array, which the plain-operand check sees when it meets tracked data.
    def make_list_args(name):
        f = getattr(np, name)
        convert = np.array

        def tracked_seq(v):
            t = type(v)
            return (t is list or t is tuple) and _seq_tracked(v, 1)

        def as_array(v):
            """The list as the array numpy would make of it. One it cannot make stays as it is, for numpy's own answer
            (an error, or False from array_equal), and its units go on record."""
            if not tracked_seq(v):
                return v
            try:
                return convert(v)
            except Exception:  # noqa: BLE001
                T._escape_prov(_any_prov(v, 0), "list_arg")
                return v

        def call(*a, **k):
            # called from the tracer's own arithmetic too, several times per read: no work without a list
            for v in a:
                t = type(v)
                if t is list or t is tuple:
                    break
            else:
                if not k:
                    return f(*a)
            if T._STATE is not None:
                a = tuple(map(as_array, a))
                if k:
                    k = {n: as_array(v) for n, v in k.items()}
            return f(*a, **k)
        functools.update_wrapper(call, f)
        call._icsa = True
        return call

    for n in _LIST_ARGS:
        if callable(getattr(np, n, None)):
            setattr(np, n, make_list_args(n))

    # What the agent's code makes with numpy is a tracked-type array holding nothing tracked, as np.zeros is: a write of
    # tracked values into it is seen, and arithmetic on it stays that type. Science's ruling on plain arrays (#2, 07:10Z).
    def make_empty(name):
        f = getattr(np, name)

        def call(*a, **k):
            r = f(*a, **k)
            if T._STATE is None or not T._is_agent_frame(2):
                return r
            if type(r) is np.ndarray:
                return _made(r)
            if type(r) in (list, tuple) and r and all(type(v) is np.ndarray for v in r):
                return type(r)(_made(v) for v in r)
            return r
        functools.update_wrapper(call, f)
        call._icsa = True
        return call

    def make_list_escapes(name):
        f = getattr(np, name)

        def call(*a, **k):
            r = f(*a, **k)
            if T._STATE is not None:
                for v in a:
                    if type(v) in (list, tuple) and _seq_tracked(v, 1):
                        T._escape_prov(_any_prov(v, 0), "list_arg")
            return r
        functools.update_wrapper(call, f)
        call._icsa = True
        return call

    for n in _LIST_ESCAPES:
        if callable(getattr(np, n, None)):
            setattr(np, n, make_list_escapes(n))

    for n in _MAKERS:
        if callable(getattr(np, n, None)):
            setattr(np, n, make_empty(n))


def _any_prov(obj, nd):
    tracked = T._collect(obj, [])
    return P.union([t._p for t in tracked], nd) if tracked else P.Prov.none()


# --------------------------------------------------------------- a run's own files
# Tracked arrays written with np.save or np.savez and read back, often in a later cell: each Sandbox.exec is a new
# interpreter, so without this the provenance stopped at the file. At the write each member's provenance goes on record, with
# the identity of its files and the fingerprint of the file written (`ownfiles.<pid>.jsonl`, `prov/own.*`). A load whose file
# has that fingerprint gets it back. Anything else stays what numpy gives: a plain array, which cannot pass as untouched: met
# with tracked data it is a plain operand, alone it leaves the sink uncovered. A write through a file object has no fingerprint
# and stays as it was (an escape). A plain array written stays plain when read back: it may hold what nothing named.
_own_files: dict[tuple[int, int], dict] = {}     # (device, inode) -> the latest record


def _note_own_file(rec: dict) -> None:
    key = (rec["st"][0], rec["st"][1])
    cur = _own_files.get(key)
    if cur is None or rec["t"] >= cur["t"]:
        _own_files[key] = rec


def _own_members(path, s=None) -> dict | None:
    """The members on record for the file at `path` (or, given `s`, the open file it is the stat of), if it is still the file
    written."""
    try:
        s = s if s is not None else os.stat(path)
    except (OSError, TypeError, ValueError):
        return None
    key = (s.st_dev, s.st_ino)
    e = _own_files.get(key)
    if e is None or e["st"][2:] != [s.st_size, s.st_mtime_ns]:
        _read_stream_records("ownfiles.*.jsonl", _note_own_file)
        e = _own_files.get(key)
    return e["members"] if e is not None and e["st"][2:] == [s.st_size, s.st_mtime_ns] else None


def _member(v):
    """(what numpy is handed, the member's record, the provenance to keep once the write succeeded)."""
    if type(v) in (list, tuple) and _seq_tracked(v, 1):
        v = np.array(v)
    if isinstance(v, T.TArray):
        if v._p.is_empty():
            return T._plain(v), {}, None
        return T._plain(v), {"shape": list(v.shape)}, v._p
    if type(v) is np.ndarray:
        return v, {"plain": True}, None
    return v, None, None


def _record_own(rp: str, members: dict, fd=None) -> None:
    st = T._STATE
    done = {}
    for name, (rec, p) in members.items():
        if rec is None:
            continue
        if p is not None:
            rec = dict(rec, prov=st.save_prov(p, "own"), files=T.files_of(p, st))
        done[name] = rec
    s = os.fstat(fd) if fd is not None else os.stat(rp)
    out = {"t": time.time(), "path": rp, "st": [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns], "members": done}
    _note_own_file(out)
    st._write("ownfiles", out)


def _restore_member(r, m):
    """A member just read, given back with what is on record for it."""
    st = T._STATE
    if st is None or m is None or type(r) is not np.ndarray or m.get("plain"):
        return r
    if "prov" not in m or P.STOPPED[0]:
        return T._wrap(r, P.Prov.none())
    if list(r.shape) != m["shape"]:
        T._count("own_file_shape_mismatch")
        return r
    t = T._tt_enter()
    try:
        return T._wrap(r, T.in_this_process(T.load_prov(st.dir / "prov" / m["prov"]), m["files"]))
    except Exception:  # noqa: BLE001 - never into agent code; stays plain
        T._count("internal_error")
        return r
    finally:
        T._tt_leave(t)


def _patch_own_files():
    orig_save, orig_savez, orig_savez_c, orig_load = np.save, np.savez, np.savez_compressed, np.load
    npz = np.lib.npyio.NpzFile
    npz_getitem = npz.__getitem__

    def path_of(file) -> str | None:
        try:
            return os.fsdecode(file) if isinstance(file, (str, bytes, os.PathLike)) else None
        except (TypeError, ValueError):
            return None

    def handle_path(file) -> str | None:
        """The path of an open file object at its start, whose content is what np.save will write. Flushed after the
        write, so that its fingerprint holds at close; a second array appended to it changes it, and it reads as plain."""
        name = getattr(file, "name", None)
        try:
            return path_of(name) if isinstance(name, (str, bytes)) and file.tell() == 0 else None
        except (OSError, ValueError, AttributeError):
            return None

    def save(*a, **k):
        file = a[0] if a else k.get("file")
        path = path_of(file) or handle_path(file)
        if T._STATE is None or path is None or (len(a) < 2 and "arr" not in k):
            return orig_save(*a, **k)
        t = T._tt_enter()
        try:
            value, rec, p = _member(a[1] if len(a) > 1 else k["arr"])
            args, kw = ((a[0], value, *a[2:]), k) if len(a) > 1 else (a, {**k, "arr": value})
            r = T._native(orig_save, *args, **kw)
            if rec is not None:
                try:
                    if path_of(file) is None:
                        file.flush()
                        _record_own(os.path.realpath(path), {"": (rec, p)}, file.fileno())
                    else:
                        _record_own(os.path.realpath(path if path.endswith(".npy") else path + ".npy"), {"": (rec, p)})
                except Exception:  # noqa: BLE001 - not on record: what is read back stays plain
                    T._count("internal_error")
            return r
        finally:
            T._tt_leave(t)
    functools.update_wrapper(save, orig_save)
    np.save = save

    def make_savez(orig):
        def savez(*a, **k):
            file = a[0] if a else k.get("file")
            path = path_of(file) or handle_path(file)
            if T._STATE is None or path is None:
                return orig(*a, **k)
            t = T._tt_enter()
            try:
                members, pos = {}, []
                for n, v in enumerate(a[1:]):
                    value, rec, p = _member(v)
                    pos.append(value)
                    members[f"arr_{n}"] = (rec, p)
                kw = {}
                for name, v in k.items():
                    if name in ("file", "allow_pickle"):
                        kw[name] = v
                        continue
                    value, rec, p = _member(v)
                    kw[name] = value
                    members[name] = (rec, p)
                r = T._native(orig, *a[:1], *pos, **kw)
                try:
                    if path_of(file) is None:
                        file.flush()
                        _record_own(os.path.realpath(path), members, file.fileno())
                    else:
                        _record_own(os.path.realpath(path if path.endswith(".npz") else path + ".npz"), members)
                except Exception:  # noqa: BLE001
                    T._count("internal_error")
                return r
            finally:
                T._tt_leave(t)
        functools.update_wrapper(savez, orig)
        return savez
    np.savez, np.savez_compressed = make_savez(orig_savez), make_savez(orig_savez_c)

    def load(*a, **k):
        file = a[0] if a else k.get("file")
        r = orig_load(*a, **k)
        if T._STATE is None:
            return r
        path = path_of(file) or path_of(getattr(file, "name", None) if isinstance(getattr(file, "name", None), (str, bytes)) else None)
        if path is None:
            return r
        t = T._tt_enter()
        try:
            if path_of(file) is None:               # an open handle: its own file, whatever the path names now
                try:
                    s = os.fstat(file.fileno())
                except Exception:  # noqa: BLE001 - not verifiable: nothing restored
                    return r
                members = _own_members(path, s)
            else:
                members = _own_members(path)
        finally:
            T._tt_leave(t)
        if isinstance(r, npz):
            r._icsa_members = members
            return r
        return _restore_member(r, members.get("")) if members else r
    functools.update_wrapper(load, orig_load)
    np.load = load

    def getitem(self, key):
        r = npz_getitem(self, key)
        members = self.__dict__.get("_icsa_members")
        if members and T._STATE is not None and isinstance(key, str):
            return _restore_member(r, members.get(key[:-4] if key.endswith(".npy") else key))
        return r
    functools.update_wrapper(getitem, npz_getitem)
    npz.__getitem__ = getitem


# --------------------------------------------------------------- fsspec and BytesIO

class _BytesIO(io.BytesIO):
    """io.BytesIO that remembers the identity of the bytes it was built from."""

    def __init__(self, initial_bytes=b"", *a, **k):
        super().__init__(initial_bytes, *a, **k)
        self._icsa_src = _bytes_ident(initial_bytes)


_BytesIO.__name__ = _BytesIO.__qualname__ = "BytesIO"
_BytesIO.__module__ = "io"


# fsspec methods whose OSError the agent sees, by operation. Each is an outer call: what a
# method catches from the calls inside it (exists, isdir, isfile, walk, cat, ...) is never
# recorded, because those run one level deeper; what escapes it is recorded at the method.
_FS_RECORD = {"ls": "list", "find": "list", "walk": "list", "glob": "list",
              "info": "stat", "exists": "stat", "lexists": "stat", "isdir": "stat", "isfile": "stat",
              "open": "open", "cat_file": "read", "get_file": "read", "cat": "read", "cat_ranges": "read",
              "copy": "read"}
_FS_ITERATES = ("walk",)
_FS_WRITE = {"open": lambda a, k: any(c in str(a[2] if len(a) > 2 else k.get("mode", "rb")) for c in "wax+"),
             "copy": lambda a, k: True}


def _wrap_fs_errors(cls):
    d = cls.__dict__
    for name, op in _FS_RECORD.items():
        f = d.get(name)
        if callable(f) and not getattr(f, "_icsa_err", False):
            w = _data_call(op, f"fsspec.{name}",
                           lambda a, k: (_fs_ident(a[0], a[1] if len(a) > 1 else next(
                               (k[n] for n in ("path", "rpath", "paths", "path1") if n in k), None)), None),
                           f, iterates=name in _FS_ITERATES, write=_FS_WRITE.get(name))
            w._icsa_err = True
            setattr(cls, name, w)


def _wrap_fs_class(cls):
    d = cls.__dict__
    if "cat_file" in d and not getattr(d["cat_file"], "_icsa", False):
        orig = d["cat_file"]

        def cat_file(self, path, start=None, end=None, **kw):
            r = orig(self, path, start=start, end=end, **kw)
            if start is None and end is None and T._STATE is not None:
                _register_bytes(r, _fs_ident(self, path))
            return r
        cat_file._icsa = True
        cls.cat_file = cat_file
    if "get_file" in d and not getattr(d["get_file"], "_icsa", False):
        orig_get = d["get_file"]

        def get_file(self, rpath, lpath, *a, **kw):
            r = orig_get(self, rpath, lpath, *a, **kw)
            if T._STATE is not None:
                try:
                    rp = os.path.realpath(os.fspath(lpath))
                    T._STATE._write("downloads", {"t": time.time(), "rpath": str(rpath), "lpath": rp})
                    if os.path.isdir(rp):           # as the client does: into a directory, under the file's own name
                        rp = os.path.join(rp, posixpath.basename(str(rpath).rstrip("/")))
                    if os.path.isfile(rp):
                        _record_download(rp, _fs_ident(self, rpath))
                except Exception:  # noqa: BLE001
                    T._count("internal_error")
            return r
        get_file._icsa = True
        cls.get_file = get_file
    _wrap_fs_errors(cls)


def _patch_fsspec():
    import fsspec.spec as S

    def walk(c):
        _wrap_fs_class(c)
        for sub in c.__subclasses__():
            walk(sub)
    walk(S.AbstractFileSystem)

    def init_subclass(cls, **kw):
        super(S.AbstractFileSystem, cls).__init_subclass__(**kw)
        _wrap_fs_class(cls)
    S.AbstractFileSystem.__init_subclass__ = classmethod(init_subclass)

    read = S.AbstractBufferedFile.read

    def fread(self, length=-1):
        start = self.loc
        r = read(self, length)
        if start == 0 and T._STATE is not None and isinstance(r, bytes) and len(r) == self.size:
            _register_bytes(r, _fs_ident(self.fs, self.path))
        return r
    S.AbstractBufferedFile.read = _data_call(
        "read", "fsspec.read", lambda a, k: (_fs_ident(a[0].fs, a[0].path), None), fread)
    io.BytesIO = _BytesIO


# --------------------------------------------------------------- install

def _lib_prefixes() -> tuple[str, ...]:
    paths = {sys.prefix, sys.base_prefix, sys.exec_prefix}
    for key in ("stdlib", "platstdlib", "purelib", "platlib"):
        try:
            paths.add(sysconfig.get_paths()[key])
        except KeyError:
            pass
    for p in sys.path:
        if "site-packages" in p or "dist-packages" in p:
            paths.add(p)
    paths.add(T._OWN_DIR)
    # Directory prefixes end with a separator: "<prefix>-agent/x.py" is not under "<prefix>".
    return tuple(sorted({os.path.realpath(p).rstrip(os.sep) + os.sep for p in paths if p}))


PATCHES = ("numpy", "masked", "h5py", "netCDF4", "xarray", "fsspec", "os", "requests", "audit")
_PATCHED: dict[str, bool] = {}

# --------------------------------------------------------------- launches
# Every child this process launches, from the interpreter's audit events: `launches.<pid>.jsonl`. A launch is matched
# offline to the start of what it launched by the ancestors in that start (a shell between them does not matter, and nothing
# passes through the environment, which the launcher can scrub); os.exec by the same pid starting again. A launched Python
# that skips the hook (python -S, a venv of its own), and a tool that is not Python, leave no start.
_LAUNCH_EVENTS = {"subprocess.Popen": (0, 1), "os.exec": (0, 1), "os.posix_spawn": (0, 1), "os.spawn": (1, 2),
                  "os.system": (None, 0), "pty.spawn": (None, 0)}
_ARG_CHARS, _ARG_ITEMS = 200, 16


_SECRETS = ("ONEDATA_TOKEN",)        # the sandbox's own credential: a command line may carry it, and the trace is kept
# Any token by its shape too, as tools/site_g_tests/lib.py's TOKEN_RE (a token the agent got elsewhere, or built): GitHub, a JWT, a
# Onedata macaroon, an X-Auth-Token header's value. The replacement has no shell syntax, and a header keeps its name and quotes,
# so a shell line still reads as its commands.
_TOKEN_SHAPES = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{15,}(?:\.[A-Za-z0-9_-]+){0,2}|MDA[xyz][A-Za-z0-9_-]{30,}"
                           r"|(?<=x-auth-token:)\s*[A-Za-z0-9._~+/=-]{20,}", re.I)


def _arg_text(v) -> str:
    try:
        t = os.fsdecode(v)
    except (TypeError, ValueError):
        t = repr(v)
    for name in _SECRETS:
        secret = _sandbox_env(name)
        if secret and len(secret) >= 8 and secret in t:
            t = t.replace(secret, f"REDACTED_{name}")
    t = _TOKEN_SHAPES.sub(lambda m: (" " if m.group(0)[:1].isspace() else "") + "REDACTED_TOKEN", t)
    return t[:_ARG_CHARS]


def _argv_cut(argv) -> list[str]:
    """As a launch and a start both record a command line, so that the two compare equal."""
    return [_arg_text(v) for v in list(argv)[:_ARG_ITEMS]]


def _program_found(exe, cwd, env) -> bool | None:
    """Whether the program is there to run. Nothing runs if it is not: a tool the image lacks, or each PATH entry os.execvp tries
    before the right one. None if that cannot be said, which counts as there."""
    try:
        exe = os.fsdecode(exe)
        if os.access(os.path.join(os.fsdecode(cwd), exe) if cwd else exe, os.X_OK):
            return True
        if os.path.dirname(exe):
            return False
        path = [os.fsdecode(d) for d in os.get_exec_path(env)]
        if any(os.access(os.path.join(d, exe), os.X_OK) for d in path):
            return True
        return None if any(not os.path.isabs(d) for d in path) else False
    except Exception:  # noqa: BLE001
        return None


_LAUNCH_OUT = threading.local()       # set while subprocess.Popen starts a process: whether its output goes into a regular file


def _to_file(v) -> bool:
    """A Popen stdout or stderr that is a regular file: an fd, or an object with one. PIPE, DEVNULL, STDOUT and None are not."""
    try:
        fd = v if type(v) is int else (v.fileno() if v is not None and hasattr(v, "fileno") else None)
        return fd is not None and fd >= 0 and stat.S_ISREG(os.fstat(fd).st_mode)
    except Exception:  # noqa: BLE001 - a stream with no descriptor writes nowhere a later read finds
        return False


def _patch_popen():
    """Science's guard on the tools that go without a start (#2, 14:59Z): one counts as exempt only when its output does not go into a
    file, which the run could read back. A shell's redirection already needs a shell to read; what is left is Popen's own stdout and
    stderr, which the audit event does not carry."""
    init = subprocess.Popen.__init__

    @functools.wraps(init)
    def __init__(self, *a, **k):
        names = ("stdin", "stdout", "stderr")
        pos = {n: a[i] for n, i in zip(names, (3, 4, 5)) if len(a) > i}        # bufsize, executable, stdin, stdout, stderr
        was = getattr(_LAUNCH_OUT, "v", None)
        _LAUNCH_OUT.v = _to_file(k.get("stdout", pos.get("stdout"))) or _to_file(k.get("stderr", pos.get("stderr")))
        try:
            return init(self, *a, **k)
        finally:
            _LAUNCH_OUT.v = was
    subprocess.Popen.__init__ = __init__


def _patch_audit():
    def hook(event, args):
        spec = _LAUNCH_EVENTS.get(event)
        if spec is None:
            return
        st = T._STATE
        if st is None:
            return
        try:
            exe_at, argv_at = spec
            argv = args[argv_at]
            argv = _argv_cut(argv) if isinstance(argv, (list, tuple)) else [_arg_text(argv)]
            exe = args[exe_at] if exe_at is not None else None
            rec = {"t": time.time(), "event": event, "exe": _arg_text(exe) if exe is not None else None, "argv": argv, "seq": _next_seq()}
            if exe is not None:
                rec["found"] = _program_found(exe, args[2] if event == "subprocess.Popen" else None, args[-1])
            if event == "subprocess.Popen" and getattr(_LAUNCH_OUT, "v", False):
                rec["out_to_file"] = True
            st._write("launches", rec)
        except Exception:  # noqa: BLE001 - an audit hook must never raise into the call
            T._count("launch_record_failed")
    sys.addaudithook(hook)
    _patch_popen()


def install(trace_dir, output_dir=None) -> T.Tracer:
    global _INSTALLED
    if T._STATE is not None:
        return T._STATE
    T._LIB_PREFIXES = _lib_prefixes()
    T._STATE = T.Tracer(Path(trace_dir), Path(output_dir) if output_dir else None)
    T._STATE.tt_write()                   # a zero record at once: a process killed before any hook still has one
    T._start_budget(trace_dir)
    T._hide_own_frames()
    T._STATE._write("events", {"t": time.time(), "kind": "start", "pid": os.getpid(), "ok_marker": T._STATE.marker_ok,
                               "versions": _versions(), "output_dir": str(T._STATE.out), "cell": T.cell_number(),
                               "ppid": os.getppid(), "ancestors": T.ancestors(), "argv": _argv_cut(sys.orig_argv)})
    _reset_local_files()
    if not _INSTALLED:
        _patch_numpy()
        _PATCHED.update(numpy=True, masked=True)
        _patch_masked()
        if T.OWN_FILES:
            _patch_own_files()
        for name, patch in (("h5py", _patch_h5py), ("netCDF4", _patch_netcdf4), ("xarray", _patch_xarray),
                            ("fsspec", _patch_fsspec), ("os", _patch_os), ("requests", _patch_requests),
                            ("audit", _patch_audit)):
            try:
                patch()
                _PATCHED[name] = True
            except ImportError:
                _PATCHED[name] = False      # a library that is not there: its reads would go unrecorded
        _INSTALLED = True
    atexit.register(_close)
    # Last: if anything above raised, the module's import fails, and no record says it loaded.
    T._STATE.write_loaded({n: bool(_PATCHED.get(n)) for n in PATCHES})
    return T._STATE


def _reset_local_files() -> None:
    _own_files.clear()
    _local_files.clear()
    _download_paths.clear()
    _written.clear()
    _local_streams_read.clear()


def _close():
    if T._STATE is not None:
        T._STATE.close()


def uninstall() -> None:
    """Stop recording (tests); the patches stay but become pass-throughs."""
    if T._STATE is not None:
        T._STATE.close()
    T._STATE = None


def install_from_env() -> T.Tracer | None:
    d = os.environ.get("ICSA_TRACE_DIR")
    if not d:
        return None
    return install(d, os.environ.get("ICSA_OUTPUT_DIR"))


def _versions() -> dict:
    out = {"python": sys.version.split()[0], "numpy": np.__version__}
    for m in ("h5py", "netCDF4", "xarray", "h5netcdf", "fsspec", "scipy", "pandas", "dask"):
        mod = sys.modules.get(m)
        if mod is not None:
            out[m] = getattr(mod, "__version__", "?")
    return out
