"""Offline layout index of `analysed_sst` in the S1/S2 files.

Built with h5py from LOCAL copies of the files (never from the agent's
connection). It maps byte ranges of a file to the elements (and so the
global units) whose bytes lie wholly inside them.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Iterable, Iterator
from pathlib import Path

import numpy as np

from .. import grid

_TOL_DEG = 1e-4


@dataclasses.dataclass(frozen=True, eq=False)
class FileLayout:
    relpath: str
    size: int
    days: np.ndarray
    lat_idx: np.ndarray
    lon_idx: np.ndarray
    shape: tuple[int, int, int]
    itemsize: int
    chunk_shape: tuple[int, int, int] | None
    chunks: np.ndarray            # (n, 6): t, j, i, byte offset, stored size, filter_mask
    contiguous: tuple[int, int] | None
    filtered: bool

    def equals(self, o: FileLayout) -> bool:
        return (self.relpath == o.relpath and self.size == o.size and self.shape == o.shape
                and self.itemsize == o.itemsize and self.chunk_shape == o.chunk_shape
                and self.contiguous == o.contiguous and self.filtered == o.filtered
                and all(np.array_equal(getattr(self, k), getattr(o, k))
                        for k in ("days", "lat_idx", "lon_idx", "chunks")))


def _attr(v):
    if isinstance(v, bytes):
        return v.decode()
    if isinstance(v, np.ndarray) and v.size == 1:
        return _attr(v.reshape(-1)[0])
    return v


def _global_days(ds) -> np.ndarray:
    import cftime
    vals = np.asarray(ds[()], dtype="f8").reshape(-1)
    units = str(_attr(ds.attrs["units"]))
    cal = str(_attr(ds.attrs.get("calendar", "standard")))
    out = np.empty(vals.size, np.int64)
    for k, c in enumerate(cftime.num2date(vals, units, cal)):
        import datetime as dt
        out[k] = grid.day_index(dt.date(c.year, c.month, c.day))
    return out


def _axis_index(vals: np.ndarray, origin: float, name: str) -> np.ndarray:
    vals = np.asarray(vals, dtype="f8")
    idx = np.rint((vals - origin) / grid.RES_DEG).astype(np.int64)
    off = np.abs(vals - (origin + idx * grid.RES_DEG))
    if vals.size and off.max() > _TOL_DEG:
        raise ValueError(f"{name} coordinate is {off.max():.6f} deg off the grid")
    n = grid.NLAT if name == "lat" else grid.NLON
    if vals.size and (idx.min() < 0 or idx.max() >= n):
        raise ValueError(f"{name} coordinate is outside the grid")
    return idx


def build_layout(path: Path, root: Path, var: str = "analysed_sst") -> FileLayout:
    import h5py
    path, root = Path(path), Path(root)
    with h5py.File(path, "r") as f:
        ds = f[var]
        if ds.ndim != 3:
            raise ValueError(f"{path}: {var} is not 3-D")
        shape = tuple(int(x) for x in ds.shape)
        days = _global_days(f["time"])
        lat = f["lat"] if "lat" in f else f["latitude"]
        lon = f["lon"] if "lon" in f else f["longitude"]
        lat_idx = _axis_index(lat[()], grid.LAT_MIN, "lat")
        lon_idx = _axis_index(lon[()], grid.LON_MIN, "lon")
        if (days.size, lat_idx.size, lon_idx.size) != shape:
            raise ValueError(f"{path}: coordinate lengths do not match shape {shape}")
        dsid = ds.id
        plist = dsid.get_create_plist()
        filtered = plist.get_nfilters() > 0
        chunk_shape = tuple(int(x) for x in ds.chunks) if ds.chunks else None
        rows: list[tuple[int, ...]] = []
        contiguous = None
        if chunk_shape is not None:
            def cb(info):
                rows.append((*(int(x) for x in info.chunk_offset), int(info.byte_offset),
                             int(info.size), int(info.filter_mask)))
            dsid.chunk_iter(cb)
        else:
            off = dsid.get_offset()
            if off is not None:
                contiguous = (int(off), int(dsid.get_storage_size()))
        chunks = np.array(rows, dtype=np.int64).reshape(-1, 6)
        itemsize = int(ds.dtype.itemsize)
    return FileLayout(path.relative_to(root).as_posix(), path.stat().st_size, days, lat_idx,
                      lon_idx, shape, itemsize, chunk_shape, chunks, contiguous, bool(filtered))


class HashlessIndex(ValueError):
    """A saved layout index whose content hashes do not name every file."""


class LayoutIndex:
    def __init__(self, layouts: dict[str, FileLayout], ids: dict[str, str] | None = None):
        self.layouts = dict(layouts)
        self.ids = dict(ids or {})       # Onedata file id -> path relative to the space (fullindex.py)
        self.shas: dict[str, str] = {}   # sha256 of a file's content -> its path; names in-memory sources
        self._depths = sorted({rel.count("/") + 1 for rel in self.layouts}, reverse=True)

    def __len__(self) -> int:
        return len(self.layouts)

    def __contains__(self, rel: str) -> bool:
        return rel in self.layouts

    def __getitem__(self, rel: str) -> FileLayout:
        return self.layouts[rel]

    def get(self, path: str) -> FileLayout | None:
        """A file by its path relative to the space, or by a full path that ends in that, in whole components (the mount's
        `/data/<space>/s1z/<name>`, the REST client's `<space>/s1z/<name>`). A base name alone identifies nothing: a copy
        of one day under another day's name would count as that day (b1 #2)."""
        p = str(path).replace("\\", "/")
        if p in self.layouts:
            return self.layouts[p]
        parts = p.split("/")
        for depth in self._depths:
            fl = self.layouts.get("/".join(parts[-depth:])) if len(parts) > depth else None
            if fl is not None:
                return fl
        return None

    def save(self, path: Path) -> None:
        rels = sorted(self.layouts)
        ls = [self.layouts[r] for r in rels]
        meta = [dict(relpath=l.relpath, size=l.size, shape=list(l.shape), itemsize=l.itemsize,
                     chunk_shape=None if l.chunk_shape is None else list(l.chunk_shape),
                     contiguous=None if l.contiguous is None else list(l.contiguous),
                     filtered=l.filtered, n_days=int(l.days.size), n_lat=int(l.lat_idx.size),
                     n_lon=int(l.lon_idx.size), n_chunks=int(l.chunks.shape[0])) for l in ls]

        def cat(k, empty):
            return np.concatenate([getattr(l, k) for l in ls]) if ls else empty

        def js(o):
            return np.frombuffer(json.dumps(o, sort_keys=True).encode(), np.uint8)
        with open(path, "wb") as fh:
            # shas and ids are saved too: an index reloaded without its content hashes names no in-memory
            # source, so every one is unidentified (#9: the validation matrix's cached index lost them)
            np.savez_compressed(
                fh, meta=np.frombuffer(json.dumps(meta).encode(), np.uint8), shas=js(self.shas), ids=js(self.ids),
                days=cat("days", np.empty(0, np.int64)),
                lat_idx=cat("lat_idx", np.empty(0, np.int64)),
                lon_idx=cat("lon_idx", np.empty(0, np.int64)),
                chunks=cat("chunks", np.empty((0, 6), np.int64)))

    def require_shas(self, where) -> None:
        """Every file must be named by its content. Without that an in-memory decode of it is unidentified, so its
        run comes out `unknown` whatever it did, and only in the options that decode from memory: an instrument
        error that looks like a result (#9, 2 Nov: 36 matrix cells; #2's pipeline would have done it to real runs)."""
        missing = set(self.layouts) - set(self.shas.values())
        if missing:
            raise HashlessIndex(f"the layout index {where} has no content hash for {len(missing)} of its "
                                f"{len(self.layouts)} files (e.g. {sorted(missing)[0]!r}); the full index is "
                                f"fullindex.load_full_index, a partial one is build_index with its hashes, saved")

    @classmethod
    def load(cls, path: Path, *, shas_from_caller: bool = False) -> LayoutIndex:
        """A saved index. Refuses one whose content hashes do not name every file (require_shas); a caller that sets
        `.shas` itself says so, and must check them (fullindex.load_full_index, from #3's manifests)."""
        with np.load(path, allow_pickle=False) as z:
            meta = json.loads(bytes(z["meta"]).decode())
            days, lat, lon, chunks = z["days"], z["lat_idx"], z["lon_idx"], z["chunks"]
            # a file saved before they were kept has neither (the full index on disk is one)
            shas = json.loads(bytes(z["shas"]).decode()) if "shas" in z.files else {}
            ids = json.loads(bytes(z["ids"]).decode()) if "ids" in z.files else {}
        out: dict[str, FileLayout] = {}
        d = a = o = c = 0
        shared_lat, shared_lon = None, None    # the same grid in every file: one array, not 15,341
        for m in meta:
            la, lo = lat[a:a + m["n_lat"]], lon[o:o + m["n_lon"]]
            if shared_lat is not None and np.array_equal(la, shared_lat):
                la = shared_lat
            else:
                la = shared_lat = la.copy()
            if shared_lon is not None and np.array_equal(lo, shared_lon):
                lo = shared_lon
            else:
                lo = shared_lon = lo.copy()
            out[m["relpath"]] = FileLayout(
                m["relpath"], m["size"], days[d:d + m["n_days"]].copy(),
                la, lo, tuple(m["shape"]),
                m["itemsize"], None if m["chunk_shape"] is None else tuple(m["chunk_shape"]),
                chunks[c:c + m["n_chunks"]].copy(),
                None if m["contiguous"] is None else tuple(m["contiguous"]), m["filtered"])
            d += m["n_days"]; a += m["n_lat"]; o += m["n_lon"]; c += m["n_chunks"]
        index = cls(out, ids)
        index.shas = shas
        if not shas_from_caller:
            index.require_shas(path)
        return index


def build_index(root: Path, files: Iterable[Path], *, hashes: bool = True) -> LayoutIndex:
    """The layouts of `files` under `root`; with `hashes`, also each file's sha256, which names an in-memory
    copy of it (the full index takes them from #3's manifests instead)."""
    files = [Path(p) for p in files]
    index = LayoutIndex({fl.relpath: fl for fl in (build_layout(p, Path(root)) for p in files)})
    if hashes:
        for p in files:
            index.shas[file_sha256(p)] = Path(p).relative_to(Path(root)).as_posix()
    return index


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def _merge(ranges) -> tuple[np.ndarray, np.ndarray]:
    r = np.asarray(list(ranges), dtype=np.int64).reshape(-1, 2)
    r = r[r[:, 1] > r[:, 0]]
    if r.shape[0] == 0:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    r = r[np.argsort(r[:, 0], kind="stable")]
    cum_end = np.maximum.accumulate(r[:, 1])
    new = np.empty(r.shape[0], bool)
    new[0] = True
    new[1:] = r[1:, 0] > cum_end[:-1]
    starts = r[new, 0]
    grp = np.cumsum(new) - 1
    ends = np.zeros(starts.size, np.int64)
    np.maximum.at(ends, grp, r[:, 1])
    return starts, ends


def _flat_to_idx(s: np.ndarray, e: np.ndarray) -> np.ndarray:
    lens = e - s
    total = int(lens.sum())
    before = np.cumsum(lens) - lens
    return np.repeat(s - before, lens) + np.arange(total, dtype=np.int64)


def covered_elements(fl: FileLayout, ranges) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """File-local (t, j, i) of every element whose bytes are all inside `ranges`."""
    empty = np.empty(0, np.int64)
    starts, ends = _merge(ranges)
    if starts.size == 0:
        return empty, empty.copy(), empty.copy()
    isz = fl.itemsize
    if fl.chunk_shape is not None:
        cs = fl.chunk_shape
        origin = fl.chunks[:, :3]
        off, size, fmask = fl.chunks[:, 3], fl.chunks[:, 4], fl.chunks[:, 5]
    elif fl.contiguous is not None:
        cs = fl.shape
        origin = np.zeros((1, 3), np.int64)
        off = np.array([fl.contiguous[0]], np.int64)
        size = np.array([fl.contiguous[1]], np.int64)
        fmask = np.zeros(1, np.int64)
    else:
        return empty, empty.copy(), empty.copy()
    nel = int(np.prod(cs))
    # Chunks that touch any merged range: ranges with end > off and start < off+size.
    lo = np.searchsorted(ends, off, side="right")
    hi = np.searchsorted(starts, off + size, side="left")
    cnt = np.maximum(hi - lo, 0)
    whole = (fmask != 0) if not fl.filtered else np.ones(off.size, bool)
    parts_k: list[np.ndarray] = []   # chunk id of each element
    parts_f: list[np.ndarray] = []   # flat element index within the chunk
    # Filtered chunks: all elements iff one merged range spans the stored bytes.
    wk = np.nonzero(whole & (cnt > 0))[0]
    if wk.size:
        l = lo[wk]
        ok = (starts[l] <= off[wk]) & (ends[l] >= off[wk] + size[wk])
        wk = wk[ok]
        if wk.size:
            parts_k.append(np.repeat(wk, nel))
            parts_f.append(np.tile(np.arange(nel, dtype=np.int64), wk.size))
    # Unfiltered chunks: (chunk, range) pairs clipped to the chunk's element bytes.
    uk = np.nonzero(~whole & (cnt > 0))[0]
    if uk.size:
        c = cnt[uk]
        kk = np.repeat(uk, c)
        rr = _flat_to_idx(lo[uk], hi[uk])
        nb = np.minimum(size[kk], nel * isz) if fl.chunk_shape is not None else size[kk]
        s = np.maximum(starts[rr], off[kk]) - off[kk]
        e = np.minimum(ends[rr], off[kk] + nb) - off[kk]
        s = -(-s // isz)
        e = e // isz
        ok = e > s
        if ok.any():
            kk, s, e = kk[ok], s[ok], e[ok]
            parts_k.append(np.repeat(kk, e - s))
            parts_f.append(_flat_to_idx(s, e))
    if not parts_k:
        return empty, empty.copy(), empty.copy()
    k = np.concatenate(parts_k)
    flat = np.concatenate(parts_f)
    t, j, i = np.unravel_index(flat, cs)
    t = t + origin[k, 0]
    j = j + origin[k, 1]
    i = i + origin[k, 2]
    keep = (t < fl.shape[0]) & (j < fl.shape[1]) & (i < fl.shape[2])
    return (t[keep].astype(np.int64), j[keep].astype(np.int64), i[keep].astype(np.int64))


_PIECE_ELEMENTS = 1 << 20              # elements of partly read chunks to expand at a time


def covered_pieces(fl: FileLayout, ranges) -> Iterator[tuple[bool, np.ndarray, np.ndarray, np.ndarray]]:
    """What `covered_elements` covers, without one array of it: a whole real S2 file is 1e10 elements (#9, 2 Nov).
    Yields (True, t, j, i), every element of t x j x i: a wholly covered chunk, never expanded; or (False, t, j, i),
    the elements listed: the covered parts of a few chunks read in part, as `covered_elements` finds them.
    A contiguous file is one chunk, so one piece; no file of the campaign's index is contiguous."""
    starts, ends = _merge(ranges)
    if starts.size == 0:
        return
    merged = list(zip(starts.tolist(), ends.tolist()))
    if fl.chunk_shape is None:
        yield (False, *covered_elements(fl, merged))
        return
    cs = fl.chunk_shape
    origin, off, size, fmask = fl.chunks[:, :3], fl.chunks[:, 3], fl.chunks[:, 4], fl.chunks[:, 5]
    lo = np.searchsorted(ends, off, side="right")
    hi = np.searchsorted(starts, off + size, side="left")
    touched = hi > lo
    whole = (fmask != 0) if not fl.filtered else np.ones(off.size, bool)
    wk = np.nonzero(whole & touched)[0]
    if wk.size:
        first = lo[wk]
        for k in wk[(starts[first] <= off[wk]) & (ends[first] >= off[wk] + size[wk])].tolist():
            t, j, i = (np.arange(int(o), min(int(o) + c, n), dtype=np.int64)
                       for o, c, n in zip(origin[k], cs, fl.shape))
            if t.size and j.size and i.size:
                yield True, t, j, i
    partial = np.nonzero(~whole & touched)[0]
    step = max(1, _PIECE_ELEMENTS // int(np.prod(cs)))
    for a in range(0, partial.size, step):
        piece = dataclasses.replace(fl, chunks=fl.chunks[partial[a:a + step]])
        yield (False, *covered_elements(piece, merged))


def to_global(fl: FileLayout, t, j, i) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return fl.days[np.asarray(t)], fl.lat_idx[np.asarray(j)], fl.lon_idx[np.asarray(i)]


def _axis_sel(entry, n: int) -> np.ndarray:
    if isinstance(entry, slice):
        return np.arange(*entry.indices(n), dtype=np.int64)
    if isinstance(entry, (int, np.integer)) and not isinstance(entry, (bool, np.bool_)):
        k = int(entry)
        if not -n <= k < n:
            raise IndexError(f"index {k} is out of bounds for axis of size {n}")
        return np.array([k % n], np.int64)
    if isinstance(entry, (list, tuple, np.ndarray)):
        a = np.asarray(entry)
        if a.ndim != 1:
            raise ValueError("array selections must be 1-D")
        if a.dtype == bool:
            if a.size != n:
                raise IndexError(f"boolean index has {a.size} entries for axis of size {n}")
            return np.nonzero(a)[0].astype(np.int64)
        if a.size == 0:
            return np.empty(0, np.int64)
        if not np.issubdtype(a.dtype, np.integer):
            raise ValueError(f"unsupported index dtype {a.dtype}")
        if a.min() < -n or a.max() >= n:
            raise IndexError("index out of bounds")
        return (a % n).astype(np.int64)
    raise ValueError(f"unsupported selection entry {entry!r}")


def selection_units(fl: FileLayout, key) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Global units of an outer-indexed selection in file index space."""
    if not isinstance(key, tuple):
        key = (key,)
    if len(key) > 3:
        raise ValueError("too many indices for a 3-D variable")
    key = key + (slice(None),) * (3 - len(key))
    t, j, i = (_axis_sel(e, n) for e, n in zip(key, fl.shape))
    tt, jj, ii = np.meshgrid(t, j, i, indexing="ij")
    return to_global(fl, tt.reshape(-1), jj.reshape(-1), ii.reshape(-1))
