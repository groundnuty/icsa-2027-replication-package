"""Read extents from byte-level traces (proxy log, FUSE trace, strace).

Each parser yields `ByteReads` (half-open byte ranges per dataset file);
`to_units` maps them through the offline layout index to the units whose
bytes were all read. Readahead makes these extents option-dependent, so they
feed cause codes and calibration, never the label (DESIGN.md).
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
import re
from collections.abc import Callable, Iterable, Iterator, Sequence

import numpy as np

from .. import grid
from ..extent import CellBox, PartedExtent
from .layout import LayoutIndex, _merge, covered_pieces, to_global
from .units import UnitTally


@dataclasses.dataclass
class ByteReads:
    ranges: dict[str, list[tuple[int, int]]] = dataclasses.field(default_factory=dict)
    unmapped: dict[str, int] = dataclasses.field(default_factory=dict)
    whole_files: set[str] = dataclasses.field(default_factory=set)

    def add(self, path: str, start: int, end: int) -> None:
        if end > start:
            self.ranges.setdefault(path, []).append((int(start), int(end)))


@dataclasses.dataclass
class ReadExtent:
    extent: PartedExtent
    files: int
    bytes_total: int | None             # None: this source knows no bytes (the ledger)
    bytes_data: int | None
    unmapped: dict[str, int]
    beyond: int                         # units read outside the required set (cells too)
    beyond_days: list[int]              # sorted day indices read outside the required days ([]: none)
    source: str = "bytes"               # "ledger": decoded by a data library; "bytes": a byte log
    downloaded_days: list[int] = dataclasses.field(default_factory=list)  # D: days of whole-file downloads
    # Days outside the required ones whose values the run decoded, in either layout: what can stand in for a missing day
    # (b3 #1). `beyond_days` is evidence about listings: on S2 it holds nothing, and on S1 it also holds files reached by
    # name, fetched for their headers or downloaded and never opened, none of which put another date's values in the run.
    other_days: list[int] = dataclasses.field(default_factory=list)


def jsonl(path, torn_ok=False) -> Iterator[dict]:
    """`torn_ok`: a stream of the tracer's own, where a line cut short by a kill is skipped (load_trace counts it as torn_trace,
    which keeps the label from resting on it); elsewhere a bad line raises."""
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except ValueError:
                    if not torn_ok:
                        raise


def proxy_reads(lines: Iterable[dict], *, kinds=("content",)) -> ByteReads:
    out = ByteReads()
    for e in lines:
        if e.get("kind") not in kinds:
            continue
        st, rng, p = e.get("status"), e.get("range"), e["path"]
        if st == 206 and rng:
            out.add(p, rng[0], rng[1] + 1)
        elif st == 200 and rng is None and e.get("method", "GET") != "HEAD":
            out.whole_files.add(p)
    return out


def fuse_reads(lines: Iterable[dict]) -> ByteReads:
    out = ByteReads()
    for e in lines:
        if e.get("op") == "read" and e.get("bytes", 0) > 0:
            out.add(e["path"], e["offset"], e["offset"] + e["bytes"])
    return out


_LINE = re.compile(r"^(?:\[pid\s+(\d+)\]\s+|(\d+)\s+)?(.*)$", re.S)
_CALL = re.compile(r"^(\w+)\((.*)\)\s+=\s+(-?\d+|\?)(?:[\s<].*)?$", re.S)
_RESUMED = re.compile(r"^<\.\.\.\s+(\w+)\s+resumed>(.*)$", re.S)
_FD = re.compile(r"^(\d+)<(.*?)>(?:,|$)", re.S)
_OPEN_RES = re.compile(r"^(\d+)<(.*)>$", re.S)


def _split_pid(raw: str) -> tuple[int, str]:
    m = _LINE.match(raw.rstrip("\n"))
    pid = m.group(1) or m.group(2)
    return (int(pid) if pid else 0), m.group(3)


def _int(s: str) -> int | None:
    try:
        return int(s.strip())
    except ValueError:
        return None


def strace_reads(text: str, *, roots: Sequence[str]) -> ByteReads:
    """Bytes returned by read/pread64/preadv on files under `roots`.

    The offset is tracked per (pid, fd): `read` advances it, `lseek` sets it
    to the returned absolute offset, `pread64`/`preadv` leave it alone, and an
    `openat` resets it. Threads sharing a descriptor under `-f` have their own
    pid and so their own offset here; HDF5 uses pread or lseek+read from one
    thread, which this handles. mmap and dup are not followed.
    """
    out = ByteReads()
    roots = tuple(r.rstrip("/") + "/" for r in roots)
    pos: dict[tuple[int, int], int] = {}
    pending: dict[int, tuple[str, str]] = {}

    def under(p: str) -> bool:
        return p.startswith(roots)

    def handle(pid: int, name: str, args: str, res: int | None) -> None:
        if res is None:
            return
        if name in ("openat", "open", "openat2"):
            if res >= 0:
                pos[(pid, res)] = 0
            return
        m = _FD.match(args)
        if m is None:
            return
        fd, path = int(m.group(1)), m.group(2)
        key = (pid, fd)
        if name == "close":
            pos.pop(key, None)
        elif name in ("lseek", "llseek"):
            if res >= 0:
                pos[key] = res
        elif name == "read":
            if res > 0:
                off = pos.get(key, 0)
                if under(path):
                    out.add(path, off, off + res)
                pos[key] = off + res
        elif name in ("pread64", "pread", "preadv", "preadv2"):
            if res > 0 and under(path):
                off = _int(args.rsplit(",", 1)[-1])
                if name == "preadv2":
                    parts = args.rsplit(",", 2)
                    off = _int(parts[-2]) if len(parts) >= 3 else None
                if off is not None:
                    out.add(path, off, off + res)

    for raw in text.splitlines():
        if not raw.strip():
            continue
        pid, body = _split_pid(raw)
        body = body.strip()
        if body.endswith("<unfinished ...>"):
            m = re.match(r"^(\w+)\((.*?)\s*<unfinished \.\.\.>$", body, re.S)
            if m:
                pending[pid] = (m.group(1), m.group(2))
            continue
        m = _RESUMED.match(body)
        if m:
            name, rest = m.groups()
            prev = pending.pop(pid, None)
            if prev is None or prev[0] != name:
                continue
            body = f"{name}({prev[1]}{rest}"
        c = _CALL.match(body)
        if not c:
            continue
        name, args, r = c.groups()
        if r == "?":
            continue
        res = int(r)
        handle(pid, name, args, res)
    return out


def _storage_intervals(fl) -> tuple[np.ndarray, np.ndarray]:
    if fl.chunk_shape is not None:
        off, size = fl.chunks[:, 3], fl.chunks[:, 4]
    elif fl.contiguous is not None:
        off, size = np.array([fl.contiguous[0]]), np.array([fl.contiguous[1]])
    else:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    return _merge(np.stack([off, off + size], axis=1))


def _overlap(s1, e1, s2, e2) -> int:
    """Total length of the intersection of two sorted disjoint interval sets."""
    if s1.size == 0 or s2.size == 0:
        return 0
    lo = np.maximum(s1[:, None], s2[None, :]) if s1.size * s2.size < 4_000_000 else None
    if lo is not None:
        hi = np.minimum(e1[:, None], e2[None, :])
        return int(np.clip(hi - lo, 0, None).sum())
    total = 0
    for a, b in zip(s1, e1):
        i = np.searchsorted(e2, a, side="right")
        j = np.searchsorted(s2, b, side="left")
        if j > i:
            total += int((np.minimum(e2[i:j], b) - np.maximum(s2[i:j], a)).sum())
    return total


_DAY_IN_NAME = re.compile(r"(?<!\d)(\d{8})(?!\d)")


def day_of_name(path: str) -> int | None:
    """The grid day of a daily data file, from its name (s1z/sst_YYYYMMDD.nc); None if it has none."""
    m = _DAY_IN_NAME.search(str(path).rsplit("/", 1)[-1])
    if m is None:
        return None
    try:
        d = grid.day_index(dt.datetime.strptime(m.group(1), "%Y%m%d").date())
    except ValueError:
        return None
    return d if 0 <= d < grid.NDAYS else None


def to_units(reads: ByteReads, index: LayoutIndex, box: CellBox, baseline_days, target_days,
             *, path_map: Callable[[str], str] | None = None) -> ReadExtent:
    pm = path_map or (lambda p: p)
    baseline_days, target_days = list(baseline_days), list(target_days)     # read twice below: an iterator would be spent by the first
    by_key: dict[str, list[tuple[int, int]]] = {}
    unmapped: dict[str, int] = {}
    named_days: set[int] = set()        # days of files not in the index, from their names
    for p in set(reads.ranges) | reads.whole_files:
        rs = list(reads.ranges.get(p, ()))
        fl = index.get(pm(p))
        if fl is None:
            s, e = _merge(rs)
            unmapped[p] = unmapped.get(p, 0) + int((e - s).sum())
            d = day_of_name(pm(p))
            if d is not None and (rs or p in reads.whole_files):
                named_days.add(d)
            continue
        if p in reads.whole_files:
            rs.append((0, fl.size))
        by_key.setdefault(fl.relpath, []).extend(rs)
    tally = UnitTally(box, baseline_days, target_days)
    files = bytes_total = bytes_data = 0
    for rel, rs in by_key.items():
        fl = index[rel]
        s, e = _merge(rs)
        n = int((e - s).sum())
        if n == 0:
            continue
        files += 1
        bytes_total += n
        ss, se = _storage_intervals(fl)
        bytes_data += _overlap(s, e, ss, se)
        for whole, t, j, i in covered_pieces(fl, list(zip(s.tolist(), e.tolist()))):
            d, la, lo = to_global(fl, t, j, i)
            (tally.add_block if whole else tally.add_units)(d, la, lo)
    required = {int(d) for d in baseline_days} | {int(d) for d in target_days}
    beyond_days = sorted((set(tally.days) | named_days) - required)
    return ReadExtent(tally.parted(), files, bytes_total, bytes_data, unmapped, tally.beyond(), beyond_days,
                      other_days=sorted(set(tally.days) - required))
