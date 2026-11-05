"""Block placement on a provider: `GET /data/{id}/distribution`, the only placement evidence M+ accepts.

A transfer's own status is not evidence: Onedata 25.0 reports `completed` for a replication that placed zero bytes and
for an eviction that removed none (PRIOR_STUDY onedata-issues 0003, 0006). Every claim about where data is comes from the
block map. Pure functions on the JSON, so they are unit-testable with hand-written maps.
"""
from __future__ import annotations

from typing import Iterable


def provider_blocks(distribution: dict, provider_id: str) -> list[tuple[int, int]]:
    """Sorted (offset, length) blocks the provider holds of one file, from a `/distribution` answer.

    A provider absent from the answer holds nothing. Blocks are `[offset, length]` per storage backend."""
    per = (distribution.get("distributionPerProvider") or {}).get(provider_id) or {}
    out: list[tuple[int, int]] = []
    for st in (per.get("distributionPerStorageBackend") or {}).values():
        for b in st.get("blocks") or []:
            out.append((int(b[0]), int(b[1])))
    return sorted(out)


def merged(blocks: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Overlapping or adjacent blocks merged, as half-open-by-length (offset, length)."""
    res: list[list[int]] = []
    for off, ln in sorted(blocks):
        if ln <= 0:
            continue
        if res and off <= res[-1][0] + res[-1][1]:
            res[-1][1] = max(res[-1][1], off + ln - res[-1][0])
        else:
            res.append([off, ln])
    return [(a, b) for a, b in res]


def held_bytes(blocks: Iterable[tuple[int, int]]) -> int:
    return sum(ln for _, ln in merged(blocks))


def uncovered(blocks: Iterable[tuple[int, int]], ranges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """The parts of `ranges` (offset, length) the blocks do not hold; empty = fully placed."""
    held = merged(blocks)
    gaps: list[tuple[int, int]] = []
    for off, ln in merged(ranges):
        pos, end = off, off + ln
        for b_off, b_ln in held:
            b_end = b_off + b_ln
            if b_end <= pos:
                continue
            if b_off >= end:
                break
            if b_off > pos:
                gaps.append((pos, b_off - pos))
            pos = max(pos, b_end)
            if pos >= end:
                break
        if pos < end:
            gaps.append((pos, end - pos))
    return gaps


def file_fully_placed(blocks: Iterable[tuple[int, int]], size: int) -> bool:
    return not uncovered(blocks, [(0, size)]) if size > 0 else True
