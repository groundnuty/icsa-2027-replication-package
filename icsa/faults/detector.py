"""The frozen detector (see DETECTOR.md). Reads ONLY a record's events, the required set and the
manifest. No scenario, injected set or label can reach it: the signature has no place for one."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Sequence

from .records.base import AccessEvent, Kind, Record
from .records.ranges import covers, merge_spans, served_spans
from .units import FileEntry, Manifest, Required

_DIR = Path(__file__).parent


@dataclasses.dataclass(frozen=True)
class DetectorSpec:
    record: Record
    version: str = "2"
    byte_rule: str = "cover_chunk"     # v2 (amendment 12): the union of served bytes covers all of the day's chunk
    audit_kinds: tuple[str, ...] = ("open", "read")
    ok_statuses: tuple[int, ...] = (200, 206)


@dataclasses.dataclass(frozen=True)
class DetectorOutput:
    record: Record
    read: frozenset[int]
    missing: frozenset[int]
    n_events: int
    n_used: int
    n_unmapped: int
    n_unresolved: int
    fingerprint: str


_FP_FILES = ["DETECTOR.md", "detector.py", "units.py", "records/base.py", "records/ranges.py",
             "records/audit.py", "records/traefik.py", "records/perf.py"]


def fingerprint(spec: DetectorSpec) -> str:
    h = hashlib.sha256()
    h.update(json.dumps(dataclasses.asdict(spec), sort_keys=True, default=str).encode())
    for name in _FP_FILES:
        h.update(name.encode())
        h.update((_DIR / name).read_bytes())
    return h.hexdigest()


def _file_of(ev: AccessEvent, manifest: Manifest, record: Record) -> FileEntry | None:
    if record is Record.TRAEFIK:
        return manifest.lookup_id(ev.target)
    return manifest.lookup_path(ev.target) or manifest.lookup_id(ev.alt_target)


def detect(events: Sequence[AccessEvent], required: Required, manifest: Manifest,
           spec: DetectorSpec) -> DetectorOutput:
    absent = [d for d in required.days if d not in manifest.units]
    if absent:
        raise ValueError(f"manifest lacks {len(absent)} required day(s), first {absent[:3]}")
    touched: set[str] = set()                       # audit: files opened/read
    served: dict[str, list[tuple[int, int]]] = {}   # byte records: spans per file
    used = unmapped = unresolved = 0
    for ev in events:
        if ev.record is not spec.record:
            raise ValueError(f"event from {ev.record.value} given to the {spec.record.value} detector")
        f = _file_of(ev, manifest, spec.record)
        relevant = ev.kind in (Kind.OPEN, Kind.READ) if spec.record is Record.AUDIT else ev.kind is Kind.READ
        if not relevant:
            continue
        if f is None:
            unmapped += 1
            continue
        if spec.record is Record.AUDIT:
            if ev.kind.value in spec.audit_kinds:
                touched.add(f.key); used += 1
        elif spec.record is Record.TRAEFIK:
            if ev.status not in spec.ok_statuses:
                continue
            sp = served_spans(ev.status, ev.range_header, ev.content_size, f.size)
            if sp is None:
                unresolved += 1
                continue
            served.setdefault(f.key, []).extend(sp); used += 1
        else:
            if ev.offset is None or ev.length is None or ev.length <= 0:
                unresolved += 1
                continue
            served.setdefault(f.key, []).append((ev.offset, min(ev.offset + ev.length, f.size))); used += 1
    if spec.byte_rule != "cover_chunk":
        raise ValueError(f"unknown byte rule {spec.byte_rule!r}")
    merged: dict[str, list[tuple[int, int]]] = {}
    read = set()
    for d in required.days:
        key, a, b = manifest.units[d]
        if spec.record is Record.AUDIT:
            if key in touched:
                read.add(d)
        else:
            if covers(merged.setdefault(key, merge_spans(served.get(key, []))), a, b):
                read.add(d)
    return DetectorOutput(spec.record, frozenset(read), frozenset(required.days) - frozenset(read),
                          len(events), used, unmapped, unresolved, fingerprint(spec))
