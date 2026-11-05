"""Box selection (#5): 25 disjoint equal-size boxes balanced on sea cells.

Sea = finite SST on every day of 1991-12-27..2003-01-05 (`seascan`). Bounds
sit midway between cell centres (lat_of(lat0) - 0.01, lat_of(lat1 - 1) + 0.01),
so any agent's inclusive lat/lon comparison selects exactly the box's cells.
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np

from .. import grid
from ..extent import CellBox

HALF = grid.RES_DEG / 2


def box_counts(sea: np.ndarray, h: int, w: int) -> np.ndarray:
    """Sea cells in every h x w window; entry [j, i] is the box starting at (j, i)."""
    ii = np.zeros((sea.shape[0] + 1, sea.shape[1] + 1), np.int64)
    ii[1:, 1:] = sea.astype(np.int64).cumsum(0).cumsum(1)
    return ii[h:, w:] - ii[:-h, w:] - ii[h:, :-w] + ii[:-h, :-w]


def bounds(box: CellBox) -> tuple[float, float, float, float]:
    """(lat_min, lat_max, lon_min, lon_max), midway between cell centres."""
    return (round(grid.lat_of(box.lat0) - HALF, 6), round(grid.lat_of(box.lat1 - 1) + HALF, 6),
            round(grid.lon_of(box.lon0) - HALF, 6), round(grid.lon_of(box.lon1 - 1) + HALF, 6))


def cells_in_bounds(lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> CellBox:
    """The cells an inclusive comparison on cell-centre coordinates selects."""
    lats = np.round(grid.LAT_MIN + np.arange(grid.NLAT) * grid.RES_DEG, 6)
    lons = np.round(grid.LON_MIN + np.arange(grid.NLON) * grid.RES_DEG, 6)
    jj = np.nonzero((lats >= lat_min) & (lats <= lat_max))[0]
    ii = np.nonzero((lons >= lon_min) & (lons <= lon_max))[0]
    return CellBox(int(jj[0]), int(jj[-1]) + 1, int(ii[0]), int(ii[-1]) + 1)


@dataclasses.dataclass(frozen=True)
class Selection:
    h: int
    w: int
    target: int
    tol: float
    boxes: list[CellBox]   # sorted by (lat0, lon0)
    sea: list[int]


def _try(cand: np.ndarray, h: int, w: int, n: int, rng: np.random.Generator, tries: int):
    # cand: (k, 2) start cells. Greedy over random orders, fixed seed.
    for _ in range(tries):
        order = rng.permutation(len(cand))
        taken: list[tuple[int, int]] = []
        for k in order:
            j, i = cand[k]
            if all(abs(j - tj) >= h or abs(i - ti) >= w for tj, ti in taken):
                taken.append((int(j), int(i)))
                if len(taken) == n:
                    return taken
    return None


def select(sea: np.ndarray, h: int, w: int, n: int = 25, tol: float = 0.02, min_sea_frac: float = 0.5,
           seed: int = 20270, tries: int = 300, step: int = 50, allowed: np.ndarray | None = None) -> Selection | None:
    """Largest target T (steps of `step` cells) for which n disjoint h x w boxes with sea
    within +-tol*T exist, each at least `min_sea_frac` sea. None if no T works."""
    cnt = box_counts(sea, h, w)
    if allowed is not None:   # eligibility: only these box starts are candidates
        cnt = np.where(allowed, cnt, -1)
    top = int(cnt.max())
    for T in range(top, math.ceil(min_sea_frac * h * w) - 1, -step):
        lo, hi = T * (1 - tol), T * (1 + tol)
        cand = np.argwhere((cnt >= lo) & (cnt <= hi) & (cnt >= min_sea_frac * h * w))
        if len(cand) < n:
            continue
        got = _try(cand, h, w, n, np.random.default_rng(seed), tries)
        if got:
            got.sort()
            boxes = [CellBox(j, j + h, i, i + w) for j, i in got]
            return Selection(h, w, T, tol, boxes, [int(cnt[j, i]) for j, i in got])
    return None
