"""Instance records (#5): built from the definition, parameterised by the period
length (kind) and a selection rule (a function returning one year pair per region).
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import json
from typing import Callable

import numpy as np

from .. import grid
from ..extent import CellBox
from ..records import Instance, Period
from . import boxes as B, required as R
from .seascan import KINDS, period_days

# A selection rule maps (kind, box list) -> list of (region index, year) pairs, 2 per region.
Rule = Callable[[str, list[CellBox]], list[tuple[int, int]]]


@dataclasses.dataclass
class InstanceRecord:
    instance: Instance
    kind: str
    sea_cells: int
    baseline_ranges: list[tuple[str, str]]    # inclusive date ranges of the method-required baseline days
    baseline_days: int                        # their count (1,452 for Jun-Aug)
    target_days: tuple[str, str, int]
    required_days: int                        # size of the day union
    required_units: int                       # sea cells x union days
    events: list[tuple[str, str]] | None = None   # ground truth, filled by groundtruth
    event_free: bool | None = None
    active_mask: str | None = None            # daily mask over the target days, '1' = active
    calibration: bool = False
    wan: bool = False
    sea_mask: dict | None = None             # {file, key, sha256}: the region's required sea cells

    def to_json(self) -> dict:
        d = dataclasses.asdict(self)
        d["instance"] = {k: (v if not isinstance(v, Period) else [v.start.isoformat(), v.end.isoformat()])
                         for k, v in dataclasses.asdict(self.instance).items()}
        d["instance"]["target"] = [self.instance.target.start.isoformat(), self.instance.target.end.isoformat()]
        return d


def build_record(index: int, region: int, box: CellBox, sea: np.ndarray, kind: str, year: int,
                 pilot: bool = False, calibration: bool = False) -> InstanceRecord:
    if kind not in KINDS:
        raise ValueError(f"unknown period kind {kind!r}")
    s, e = period_days(kind, year)
    la0, la1, lo0, lo1 = B.bounds(box)
    inst = Instance(f"I{index:02d}", f"R{region:02d}", la0, la1, lo0, lo1,
                    box.lat0, box.lat1, box.lon0, box.lon1, Period(s, e), pilot, calibration)
    base, tgt = R.method_baseline_day_indices(s, e), R.target_day_indices(s, e)
    union = np.union1d(base, tgt)
    nsea = int(sea.sum())
    return InstanceRecord(
        inst, kind, nsea,
        [(a.isoformat(), b.isoformat()) for a, b in R.method_baseline_ranges(s, e)], int(base.size),
        (s.isoformat(), e.isoformat(), int(tgt.size)),
        int(union.size), nsea * int(union.size), calibration=calibration)


def build_records(boxes: list[CellBox], seas: list[np.ndarray], kind: str, rule: Rule) -> list[InstanceRecord]:
    picks = rule(kind, boxes)
    counts = {}
    for r, _ in picks:
        counts[r] = counts.get(r, 0) + 1
    if sorted(counts) != list(range(len(boxes))) or set(counts.values()) != {2}:
        raise ValueError("a rule must give exactly two periods per region")
    for r in counts:
        ys = [y for rr, y in picks if rr == r]
        if ys[0] == ys[1]:
            raise ValueError(f"region {r}: periods are not disjoint")
    return [build_record(i, r, boxes[r], seas[r], kind, y) for i, (r, y) in enumerate(picks)]


def seeded_rule(seed: int, years=range(2003, 2023)) -> Rule:
    def rule(kind, boxes):
        rng = np.random.default_rng(seed)
        out = []
        for r in range(len(boxes)):
            ys = sorted(int(y) for y in rng.choice(list(years), 2, replace=False))
            out += [(r, ys[0]), (r, ys[1])]
        return out
    return rule


def dump(records: list[InstanceRecord]) -> str:
    return json.dumps([r.to_json() for r in records], indent=1)
