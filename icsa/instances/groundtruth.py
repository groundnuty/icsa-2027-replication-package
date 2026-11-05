"""Ground truth of one (region, period): regional mode (c) of the reference
detector, computed mode on the S1 values (#4). Thresholds come from the
baseline 1991-12-27..2003-01-05 (+-5-day pooling is inside the reference);
per-cell detection runs on the target period only; the event-end rule is
applied to the region's sea cells.
"""
from __future__ import annotations

import dataclasses
import datetime as dt

import numpy as np

from .. import grid
from ..extent import CellBox
from .. import refdet
from . import required as R


@dataclasses.dataclass(frozen=True)
class Truth:
    events: list[tuple[dt.date, dt.date]]
    active: np.ndarray       # bool (n_target_days,): the daily mask
    cell_mask: np.ndarray    # bool (n_target_days, h, w)


def sea_for(box: CellBox, sst_base: np.ndarray, sst_target: np.ndarray) -> np.ndarray:
    """The prompt's definition: finite on every baseline and every target day."""
    return np.isfinite(sst_base).all(0) & np.isfinite(sst_target).all(0)


def fields_for(box: CellBox, sst_base: np.ndarray) -> refdet.Fields:
    return refdet.computed_fields(sst_base, R.baseline_day_indices(), box)


def truth(box: CellBox, fields: refdet.Fields, sst_target: np.ndarray, target_days: np.ndarray,
          sea: np.ndarray) -> Truth:
    det = refdet.detect(sst_target, target_days, box, fields, sea)
    ev = [(grid.day_date(e.onset), grid.day_date(e.end)) for e in det.events]
    return Truth(ev, det.active, det.cell_mask)


def reference_truth(box: CellBox, region: int, target_days: np.ndarray, sea: np.ndarray | None = None):
    """Ground truth through the shared reference path `refdet.ground_truth` (the one scoring uses),
    reading the per-box SST cache. With sea=None its own sea-cell rule applies (finite on every day of
    1991-12-27..2003-01-05 and of the target period)."""
    from ..refdet import truth as RT
    from . import cache

    def loader(b, days):
        assert b == box
        return cache.load(region, days)

    return RT.ground_truth(box, target_days, loader=loader, sea=sea)
