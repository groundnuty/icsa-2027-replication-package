"""An outside view of each run: what the logs delivered against what the tracer saw (#9).

The ledger and the listing stream live in the agent's process, as the analysed extent does, so a read
they miss is missed by both. The gate's log (T, T-unpaginated, D) and oneclient's performance log (M,
M+) are written outside it. Science's conditions (#9, 1 Nov): compare at file level in S1 and chunk
level in S2, not by counts, and never touch a label.

- `listing_disagrees`: the number of /children requests, and those carrying a token, differ between
  the gate and the tracer (a listing by httpx, urllib or a subprocess passes the gate, not the hook).
  The cause coder routes such a run to `listing_evidence_incomplete`.
- `decoded_not_delivered`: the ledger names a file (S1) or a chunk (S2) no log delivered. It should
  never happen; each such run goes to code inspection.
- `delivered_not_decoded`: a log delivered a file or chunk the tracer never saw decoded, on a run
  labelled omitting: a stratum of the audit (#35).

Read-ahead moves bytes nobody asked for, so it is kept out of the second comparison. In S1 it cannot
cross a file, so file level is immune. In S2 a read's trailing read-ahead is trimmed: the last
READAHEAD_BYTES of each run of delivered bytes never count as delivered on purpose (T: the client's
5 MiB block, seen as every range in the real gate logs; M: only FsLogic reads count, not ReadCache
prefetch, and the trim covers the kernel's FUSE read-ahead, about 1 MiB in the real perf log). D moves
whole files by design, so in S2 it compares the file only. `decoded_not_delivered` needs no such care:
what was decoded was delivered, read-ahead or not.

A view that is absent is `None`, never agreement.
"""
from __future__ import annotations

import csv
import re
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from .layout import LayoutIndex, _merge
from .readext import ByteReads

READAHEAD_BYTES = {"T": 5 * 2**20 + 8, "T-unpaginated": 5 * 2**20 + 8, "M": 2**20, "M+": 2**20}
MAX_LISTED = 50                         # names kept per list in the flags; the counts are whole
_REAL_CONTENT = re.compile(r"/data/([^/]+)/content$")
_RANGE = re.compile(r"^bytes=(\d+)-(\d*)$")
_SUFFIX = re.compile(r"^bytes=-(\d+)$")


def file_sizes(index) -> dict[str, int] | None:
    layouts = getattr(index, "layouts", None)
    return None if layouts is None else {rel: int(fl.size) for rel, fl in layouts.items()}


def gate_reads(lines: Iterable[dict], ids: dict[str, str] | None = None,
               sizes: dict[str, int] | None = None) -> tuple[ByteReads, int]:
    """Bytes the gate delivered to the sandbox, per dataset file, and the content requests whose
    file id the index does not know. Only bytes the gate recorded as sent count: a range it cannot place
    (a suffix range of a file of unknown size, an unparsed range) counts nothing, and a 200 counts as the
    whole file only if the file's size is known, it sent that many bytes and was not cut short; otherwise the
    prefix it sent."""
    out = ByteReads()
    unknown = 0
    for r in lines:
        if r.get("tag") != "content" or r.get("decision") != "allow" or r.get("status") not in (200, 206):
            continue
        path = str(r.get("path", ""))
        m = _REAL_CONTENT.search(path)
        if m:
            rel = (ids or {}).get(m.group(1))
            if rel is None:
                unknown += 1
                continue
        else:
            rel = path[len("/data/"):] if path.startswith("/data/") else path   # the local server
        sent = int(r.get("bytes") or 0)
        size = (sizes or {}).get(rel)
        if r.get("status") == 206:
            rng = _RANGE.match(str(r.get("range") or ""))
            suf = _SUFFIX.match(str(r.get("range") or ""))
            if rng:
                start = int(rng.group(1))
            elif suf and size is not None:
                start = max(size - int(suf.group(1)), 0)
            else:
                continue                                   # a range that cannot be placed: nothing counted
            if sent:
                out.add(rel, start, start + sent)
            continue
        if r.get("client_aborted") or size is None or sent < size:
            if sent:
                out.add(rel, 0, sent)                      # a 200 not shown whole: the prefix it sent
            continue
        out.whole_files.add(rel)
    return out, unknown


def gate_truncated_downloads(lines: Iterable[dict], ids: dict[str, str] | None, sizes: dict[str, int]) -> int:
    """Whole-file downloads (a 200 with no range) the gate shows cut short: `causes.truncated_downloads` for the log a
    real run has. Only files in `sizes` count; `ids` maps a real request's file id to its path."""
    n = 0
    for r in lines:
        if r.get("tag") != "content" or r.get("decision") != "allow" or r.get("status") != 200 \
                or r.get("range") is not None or r.get("method", "GET") == "HEAD":
            continue
        path = str(r.get("path", ""))
        m = _REAL_CONTENT.search(path)
        rel = (ids or {}).get(m.group(1)) if m else (path[len("/data/"):] if path.startswith("/data/") else path)
        if rel in sizes and (r.get("client_aborted") or int(r.get("bytes") or 0) < sizes[rel]):
            n += 1
    return n


def gate_listing(lines: Iterable[dict]) -> dict[str, int]:
    n = t = 0
    for r in lines:
        if r.get("tag") == "children" and r.get("method") == "GET":
            n += 1
            t += "token=" in str(r.get("query") or "")
    return {"requests": n, "with_token": t}


def tracer_listing(http_lines: Iterable[dict]) -> dict[str, int]:
    n = t = 0
    for r in http_lines:
        if r.get("method") == "GET":
            n += 1
            t += r.get("token") is not None
    return {"requests": n, "with_token": t}


def perf_reads(csv_paths: Iterable[Path]) -> ByteReads:
    """FsLogic reads of oneclient's performance log (--log-read-write-perf): what the FUSE layer
    delivered. ReadCache rows (its prefetch and the reads behind it) never reached the agent."""
    out = ByteReads()
    for p in csv_paths:
        with open(p, newline="") as fh:
            for row in csv.DictReader(fh):
                row = {str(k).strip().lower(): v for k, v in row.items()}
                if row.get("class") == "FsLogic" and row.get("operation") == "read":
                    start = int(row["offset"])
                    out.add(row["file"], start, start + int(row["size"]))
    return out


def _delivered_chunks(fl, reads: ByteReads, path: str, trim: int) -> tuple[set[int], bool]:
    """(time indices of the chunks wholly delivered, with `trim` bytes off the end of each run of
    delivered bytes; whether any byte of the file was delivered)."""
    whole = path in reads.whole_files
    rs = list(reads.ranges.get(path, ()))
    if not whole and not rs:
        return set(), False
    if whole:
        rs.append((0, fl.size))
    s, e = _merge(rs)
    e = np.maximum(s, e - (0 if whole else trim))
    out = set()
    if fl.chunk_shape is None or not len(fl.chunks):
        return out, True
    i = np.searchsorted(s, fl.chunks[:, 3], side="right") - 1
    ok = (i >= 0) & (fl.chunks[:, 3] + fl.chunks[:, 4] <= e[np.maximum(i, 0)])
    return {int(t) for t in fl.chunks[ok, 0]}, True


def compare(option: str, reads: ByteReads, decoded: dict[str, set[int]], index: LayoutIndex) -> dict:
    """File level where a file holds one day (S1), chunk level where it holds many (S2)."""
    paths = {}
    for p in set(reads.ranges) | reads.whole_files:
        fl = index.get(p)
        if fl is not None:
            paths.setdefault(fl.relpath, []).append(p)
    not_delivered, not_decoded = [], []
    for rel in sorted(set(decoded) | set(paths)):
        fl = index[rel]
        ts = decoded.get(rel, set())
        got, any_bytes = set(), False
        # every spelling of the path a log used (a mount's path, the index's)
        merged = ByteReads()
        for p in paths.get(rel, ()):
            merged.ranges.setdefault(rel, []).extend(reads.ranges.get(p, ()))
            if p in reads.whole_files:
                merged.whole_files.add(rel)
        got_all, any_bytes = _delivered_chunks(fl, merged, rel, 0)
        if int(fl.days.size) <= 1:                     # S1: one day, file level
            if ts and not any_bytes:
                not_delivered.append(rel)
            if any_bytes and not ts:
                not_decoded.append(rel)
            continue
        missing = sorted(ts - got_all)                  # read-ahead cannot hide a decoded chunk
        not_delivered += [f"{rel}#{t}" for t in missing]
        if option == "D":
            # Only deliveries the agent chose count (science, #9 19:52Z, amendment 2): D delivers the whole S2
            # file by design, so its chunks are never "delivered, not decoded". D in S1 stays (file level).
            continue
        got, _ = _delivered_chunks(fl, merged, rel, READAHEAD_BYTES.get(option, 0))
        not_decoded += [f"{rel}#{t}" for t in sorted(got - ts)]
    return {"decoded_not_delivered": not_delivered, "delivered_not_decoded": not_decoded}


def cross_check(option: str, label: str, *, decoded: dict[str, set[int]], index: LayoutIndex,
                gate_lines: list[dict] | None, perf_csvs: list[Path] | None, local_reads: ByteReads | None,
                http_lines: list[dict]) -> dict:
    """The run's cross-check, for `flags`. Booleans are None when no outside view exists."""
    rest = option in ("T", "T-unpaginated", "D")
    source, reads, unknown = None, None, 0
    listing_view = None
    if rest and gate_lines is not None:
        source = "gate"
        reads, unknown = gate_reads(gate_lines, getattr(index, "ids", None), file_sizes(index))
        listing_view = {"tracer": tracer_listing(http_lines), "gate": gate_listing(gate_lines)}
    elif not rest and perf_csvs:
        source = "oneclient_perf"
        reads = perf_reads(perf_csvs)
    elif not rest and local_reads is not None:
        source = "strace"                               # the local path: M has no oneclient there
        reads = local_reads
    out = {"source": source, "listing": listing_view, "unknown_file_ids": unknown,
           "listing_disagrees": None if listing_view is None else listing_view["tracer"] != listing_view["gate"],
           "decoded_not_delivered": None, "delivered_not_decoded": None,
           "decoded_not_delivered_items": 0, "delivered_not_decoded_items": 0, "examples": {}}
    if reads is None:
        return out
    c = compare(option, reads, decoded, index)
    dnd, ndd = c["decoded_not_delivered"], c["delivered_not_decoded"]
    out.update(decoded_not_delivered=bool(dnd), decoded_not_delivered_items=len(dnd),
               delivered_not_decoded=bool(ndd) and label == "omitting", delivered_not_decoded_items=len(ndd),
               examples={"decoded_not_delivered": dnd[:MAX_LISTED], "delivered_not_decoded": ndd[:MAX_LISTED]})
    return out
