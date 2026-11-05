"""Units, required set and the dataset manifest.

The unit of calibration is one **day** in both layouts: an S1 file holds one day, and an S2 chunk is
(1, 626, 1051), one day. `Required` is the instance's required set of days; `Manifest` is STATIC
dataset metadata (which file holds which day, and which bytes hold its data). The manifest is built
from the dataset files themselves (HDF5 chunk index), never from a run's record or a scenario.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import re
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np

from icsa import grid
from icsa.extent import PartedExtent
from icsa.records import Layout


@dataclasses.dataclass(frozen=True)
class Required:
    """Required days of one instance, with the baseline/target split kept."""

    baseline: frozenset[int]
    target: frozenset[int]

    @property
    def days(self) -> tuple[int, ...]:
        return tuple(sorted(self.baseline | self.target))

    @classmethod
    def from_parted(cls, pe: PartedExtent) -> "Required":
        """From the shared extent type (#5 supplies the instance's required PartedExtent)."""
        b = frozenset(int(d) for d in pe.baseline.days[pe.baseline.mask.any(axis=(1, 2))])
        t = frozenset(int(d) for d in pe.target.days[pe.target.mask.any(axis=(1, 2))])
        return cls(b, t)

    @classmethod
    def from_days(cls, baseline: Iterable[int], target: Iterable[int]) -> "Required":
        return cls(frozenset(int(d) for d in baseline), frozenset(int(d) for d in target))


@dataclasses.dataclass(frozen=True)
class FileEntry:
    key: str                  # stable id inside the manifest
    rel_path: str             # path below the space, no leading slash
    size: int
    object_id: str | None = None   # REST file id (T and D see only this)
    uuid: str | None = None


@dataclasses.dataclass(frozen=True, eq=False)
class Manifest:
    """day -> (file key, data start, data end) in bytes (half-open), plus the file table."""

    layout: Layout
    files: tuple[FileEntry, ...]
    units: Mapping[int, tuple[str, int, int]]

    def __post_init__(self) -> None:
        keys = {f.key: f for f in self.files}
        if len(keys) != len(self.files):
            raise ValueError("duplicate file keys")
        per_file: dict[str, list[tuple[int, int]]] = {}
        for d, (k, a, b) in self.units.items():
            if k not in keys:
                raise ValueError(f"unit {d}: unknown file {k}")
            if not 0 <= a < b <= keys[k].size:
                raise ValueError(f"unit {d}: span {a}..{b} outside file {k} of {keys[k].size} B")
            per_file.setdefault(k, []).append((a, b))
        for k, spans in per_file.items():
            spans.sort()
            for (a0, b0), (a1, b1) in zip(spans, spans[1:]):
                if a1 < b0:
                    raise ValueError(f"file {k}: unit spans overlap")
        if self.layout is Layout.S1 and any(len(v) != 1 for v in per_file.values()):
            raise ValueError("S1: one unit per file")
        if self.layout is Layout.S2 and len(self.files) != 1:
            raise ValueError("S2: exactly one file")
        object.__setattr__(self, "_by_key", keys)

    def file(self, key: str) -> FileEntry:
        return self._by_key[key]  # type: ignore[attr-defined]

    def file_of_unit(self, day: int) -> FileEntry:
        return self.file(self.units[day][0])

    def span(self, day: int) -> tuple[int, int]:
        _, a, b = self.units[day]
        return a, b

    def data_start(self, key: str) -> int:
        """First data byte of the file: everything below it is header and metadata."""
        return min(a for k, a, _ in self.units.values() if k == key)

    def units_of(self, key: str) -> list[int]:
        return sorted(d for d, (k, _, _) in self.units.items() if k == key)

    def _index(self) -> tuple[dict, dict]:
        """{rel path: file} and {object id or uuid: file}, built on first use (a manifest unpickled from a plan has neither)."""
        ix = self.__dict__.get("_lookup")
        if ix is None:
            by_rel: dict[str, tuple[int, FileEntry]] = {}
            by_id: dict[str, FileEntry] = {}
            for n, f in enumerate(self.files):
                key = f.rel_path.strip("/")
                if key not in by_rel or len(f.rel_path) > len(by_rel[key][1].rel_path):
                    by_rel[key] = (n, f)
                for i in (f.object_id, f.uuid):
                    if i:
                        by_id.setdefault(i, f)
            ix = (by_rel, by_id)
            object.__setattr__(self, "_lookup", ix)
        return ix

    def lookup_path(self, path: str | None) -> FileEntry | None:
        """Match a logged path by its tail, on a '/' boundary: the logs prefix a space name or id. Of several matches, the longest
        rel_path as written, then the first in the file table."""
        if not path or path in ("null", "undefined"):
            return None
        tail = path.strip("/")
        by_rel = self._index()[0]
        best = None
        while True:
            hit = by_rel.get(tail)
            if hit is not None and (best is None or len(hit[1].rel_path) > len(best[1].rel_path)
                                    or (len(hit[1].rel_path) == len(best[1].rel_path) and hit[0] < best[0])):
                best = hit
            cut = tail.find("/")
            if cut < 0:
                return best[1] if best else None
            tail = tail[cut + 1:]

    def lookup_id(self, ident: str | None) -> FileEntry | None:
        if not ident:
            return None
        return self._index()[1].get(ident)


# ---- builders from the dataset files (static metadata) -------------------------------------
_S1_NAME = re.compile(r"sst_(\d{4})(\d{2})(\d{2})\.nc$")


def _dataset_spans(path: Path, var: str) -> list[tuple[int, int, int]]:
    """[(index along axis 0, byte start, byte end)] of the variable's data, from the HDF5 layout."""
    import h5py

    from icsa.ncio import NETCDF_LOCK
    with NETCDF_LOCK, h5py.File(path, "r") as h:
        ds = h[var]
        spans = []
        if ds.chunks is not None:
            for i in range(ds.id.get_num_chunks()):
                ci = ds.id.get_chunk_info(i)
                spans.append((int(ci.chunk_offset[0]), int(ci.byte_offset), int(ci.byte_offset + ci.size)))
        else:
            off, size = ds.id.get_offset(), ds.id.get_storage_size()
            if off is None or size == 0:
                raise ValueError(f"{path}: {var} has no stored data")
            spans.append((0, int(off), int(off + size)))
    return sorted(spans)


def build_s1_manifest(root: Path, rel_dir: str = "", var: str = "analysed_sst",
                      ids: Mapping[str, str] | None = None) -> Manifest:
    """One file per day, named sst_YYYYMMDD.nc; each file one chunk (or contiguous)."""
    files, units = [], {}
    for p in sorted(root.glob("sst_*.nc")):
        m = _S1_NAME.search(p.name)
        if not m:
            continue
        day = grid.day_index(dt.date(*map(int, m.groups())))
        spans = _dataset_spans(p, var)
        if len(spans) != 1:
            raise ValueError(f"{p}: S1 file must hold one chunk, found {len(spans)}")
        rel = f"{rel_dir.strip('/')}/{p.name}".strip("/")
        files.append(FileEntry(p.name, rel, p.stat().st_size, (ids or {}).get(p.name)))
        units[day] = (p.name, spans[0][1], spans[0][2])
    return Manifest(Layout.S1, tuple(files), units)


def build_s2_manifest(path: Path, rel_path: str, var: str = "analysed_sst",
                      object_id: str | None = None) -> Manifest:
    """One file chunked (1, lat, lon) along time: chunk index along axis 0 is the day."""
    spans = _dataset_spans(path, var)
    f = FileEntry(path.name, rel_path, path.stat().st_size, object_id)
    return Manifest(Layout.S2, (f,), {i: (f.key, a, b) for i, a, b in spans})
