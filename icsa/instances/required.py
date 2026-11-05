"""The required extent of an instance, built from the definition only (#5).

required = sea cells of the region x (the method-required baseline days U the target days);
sea = finite on every target day. For a Jun-Aug target the baseline part is 12 May..20 Sep of
each year 1992..2002 (1,452 days). It is never derived from what a reference or a run read.
The baseline and target parts are kept apart (`icsa.extent.PartedExtent`).
`baseline_day_indices` (1991-12-27..2003-01-05, 4,028 days) is only the pooling superset the
reference reads for its cached fields.
"""
from __future__ import annotations

import datetime as dt

import numpy as np

from .. import grid
from ..extent import CellBox, Extent, PartedExtent

# Pooling superset, used for the cached fields and the sea scan (NOT the required extent):
BASE_START = dt.date(1991, 12, 27)
BASE_END = dt.date(2003, 1, 5)
N_BASELINE_DAYS = 4028
S1_PATTERN = "sst_{:%Y%m%d}.nc"
S2_CHUNK = (1, grid.NLAT, grid.NLON)


def baseline_day_indices() -> np.ndarray:
    d = np.arange(grid.day_index(BASE_START), grid.day_index(BASE_END) + 1, dtype=np.int64)
    assert d.size == N_BASELINE_DAYS
    return d


def target_day_indices(start: dt.date, end: dt.date) -> np.ndarray:
    return np.arange(grid.day_index(start), grid.day_index(end) + 1, dtype=np.int64)


POOL_HALF = 5       # +-5-day pooling window of the threshold
SMOOTH_HALF = 15    # circular 31-day moving mean
METHOD_HALF = POOL_HALF + SMOOTH_HALF   # 20 days
BASELINE_YEARS = (1992, 2002)


def method_baseline_ranges(start: dt.date, end: dt.date) -> list[tuple[dt.date, dt.date]]:
    """The baseline days the method needs for a target period (science ruling, #5/#9): for every
    baseline year 1992..2002 the same calendar dates as the target, widened by 20 days
    (+-5 pooling plus +-15 smoothing), intersected with 1992-01-01..2002-12-31.
    Jun 1..Aug 31 -> 12 May..20 Sep of each year = 132 days x 11 years = 1,452 days."""
    out = []
    for y in range(BASELINE_YEARS[0], BASELINE_YEARS[1] + 1):
        a = dt.date(y, start.month, start.day) - dt.timedelta(METHOD_HALF)
        b = dt.date(y, end.month, end.day) + dt.timedelta(METHOD_HALF)
        a, b = max(a, grid.BASELINE[0]), min(b, grid.BASELINE[1])
        if out and a <= out[-1][1] + dt.timedelta(1):   # overlapping or adjacent: merge
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def method_baseline_day_indices(start: dt.date, end: dt.date) -> np.ndarray:
    return np.concatenate([target_day_indices(a, b) for a, b in method_baseline_ranges(start, end)])


def required_extent(box: CellBox, sea: np.ndarray, start: dt.date, end: dt.date) -> PartedExtent:
    """`sea`: bool (h, w) over the box, finite on every target day. Baseline part = the
    method-required days (`method_baseline_day_indices`), target part = the target days."""
    return PartedExtent(Extent.full(box, method_baseline_day_indices(start, end), sea),
                        Extent.full(box, target_day_indices(start, end), sea))


def union_days(start: dt.date, end: dt.date) -> np.ndarray:
    return np.union1d(method_baseline_day_indices(start, end), target_day_indices(start, end))


def s1_files(days: np.ndarray) -> list[str]:
    return [S1_PATTERN.format(grid.day_date(int(i))) for i in days]


def s2_chunks(days: np.ndarray) -> list[tuple[int, int, int]]:
    """One chunk (1, 626, 1051) per day: the chunk index is (time index, 0, 0)."""
    return [(int(i), 0, 0) for i in days]
