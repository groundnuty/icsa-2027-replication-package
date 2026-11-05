"""The report's own account of its extent vs the instrumented envelope.

Descriptive only (protocol/report-spec.md: `region`, `baseline_analysed` and
`target_analysed` are bounding envelopes; actual coverage comes only from the
instruments and the mask). Exact comparison, no tolerance except the 0.001 deg
coordinate matching rule for the region:
  region    do the stated bounds select the same grid cells as the bounding box
            of the instrumented analysed cells? A cell is selected iff its
            centre lies within the bounds, extended by 0.001 deg;
  baseline / target  do the stated start and end equal the first and last
            analysed day? Plus the signed day differences (stated - instrumented).
A stated null range matches iff nothing was instrumented for it.
"""
from __future__ import annotations

import numpy as np

from .. import grid
from ..extent import Extent, PartedExtent
from .report import COORD_TOL_DEG, Report


def _selected(lo: float, hi: float, origin: float, n: int) -> tuple[int, int] | None:
    """Half-open index range of the grid cells whose centre is within [lo, hi] (+- tol)."""
    c = origin + np.arange(n) * grid.RES_DEG
    idx = np.flatnonzero((c >= lo - COORD_TOL_DEG) & (c <= hi + COORD_TOL_DEG))
    return (int(idx[0]), int(idx[-1]) + 1) if idx.size else None


def _cell_box(parts: list[Extent]) -> tuple[int, int, int, int] | None:
    box = parts[0].box
    any_cell = np.zeros(box.shape, bool)
    for e in parts:
        if e.days.size:
            any_cell |= e.mask.any(axis=0)
    if not any_cell.any():
        return None
    rows, cols = np.flatnonzero(any_cell.any(axis=1)), np.flatnonzero(any_cell.any(axis=0))
    return (box.lat0 + int(rows[0]), box.lat0 + int(rows[-1]) + 1,
            box.lon0 + int(cols[0]), box.lon0 + int(cols[-1]) + 1)


def _days(e: Extent) -> tuple[int, int] | None:
    d = e.days[e.mask.any(axis=(1, 2))] if e.days.size else e.days
    return (int(d[0]), int(d[-1])) if d.size else None


def _range(stated, env) -> dict:
    if stated is None:
        return {"matches": env is None, "start_diff_days": None, "end_diff_days": None}
    if env is None:
        return {"matches": False, "start_diff_days": None, "end_diff_days": None}
    s, e = (stated[0] - grid.DAY0).days, (stated[1] - grid.DAY0).days
    return {"matches": (s, e) == env, "start_diff_days": s - env[0], "end_diff_days": e - env[1]}


def extent_account(report: Report, analysed: PartedExtent) -> dict:
    lat_min, lat_max, lon_min, lon_max = report.region
    env = _cell_box([analysed.baseline, analysed.target])
    stated = (_selected(lat_min, lat_max, grid.LAT_MIN, grid.NLAT),
              _selected(lon_min, lon_max, grid.LON_MIN, grid.NLON))
    stated_box = None if None in stated else (*stated[0], *stated[1])
    return {"region_matches": env is not None and stated_box == env,
            "baseline": _range(report.baseline, _days(analysed.baseline)),
            "target": _range(report.target, _days(analysed.target))}
