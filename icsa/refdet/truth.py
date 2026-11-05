"""Ground truth (protocol/parameters.md, reference rule; #4 comment of 31 Oct 20:55Z): computed mode
on the S1 values the agents read, with the frozen method (Hazen percentile, calendar-neighbour pooling
including the 5 days either side of the baseline, day 60 interpolated before smoothing, circular
31-day mean, float64 throughout), never the published fields. Sea cells follow the prompt's rule
(`sea_cells`): finite on every day of the required baseline extent and of the target period.

Fields come from the full-domain cache (`fieldcache.build`, default `DEFAULT_CACHE`) when one is
given, else they are computed from the box's baseline days; both give the same fields, because every
cell is computed independently of its neighbours. A cache is used only after
`fieldcache.check_ground_truth` accepts it: the frozen baseline and padded extent, Hazen, float64, the
sea rule, and, on the production path (S1), the fingerprint of the S1 files it was built from equal
to that of the files on disk now. Anything else raises; there is no fallback.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np

from .. import paths
from ..extent import CellBox
from . import Detection, computed_fields, detect, fieldcache, load_sst, required_baseline_days, sea_cells

DEFAULT_CACHE = paths.DATA_ROOT / "refdet" / "fields_s1"


def _s1(box: CellBox, days: np.ndarray) -> np.ndarray:
    return load_sst(box, days, "s1")


def ground_truth(box: CellBox, target_days: np.ndarray, *, cache_dir: Path | str | None = None,
                 loader: Callable[[CellBox, np.ndarray], np.ndarray] | None = None,
                 sea: np.ndarray | None = None, cache_source: str | None = None,
                 cache_fingerprint: str | None = None, cache_grid: tuple[int, int] | None = None) -> Detection:
    """Per-cell detection on the target days of `box`, then the region event rule. `sea` overrides the
    sea-cell rule (tests only). With the default S1 loader a cache must record source "s1", the current
    S1 fingerprint and the product grid. With another loader a cache can be used only when the caller
    states what it must hold: `cache_source` and `cache_grid` (nlat, nlon) are required, and
    `cache_fingerprint` is checked when given; nothing is taken from the cache's own record."""
    target_days = np.asarray(target_days, np.int64)
    loader = loader or _s1
    sst_t = loader(box, target_days)
    if cache_dir is not None:
        if loader is _s1:
            fieldcache.check_ground_truth(cache_dir, source=fieldcache.S1_SOURCE,
                                          source_fingerprint=fieldcache.s1_fingerprint(required_baseline_days()))
        else:
            if cache_source is None or cache_grid is None:
                raise ValueError("a cache with a custom loader needs cache_source and cache_grid: the expected "
                                 "source and grid must come from the caller, not from the cache")
            fieldcache.check_ground_truth(cache_dir, source=cache_source, source_fingerprint=cache_fingerprint,
                                          nlat=cache_grid[0], nlon=cache_grid[1])
        fields = fieldcache.load(box, cache_dir)
        fin_b = fieldcache.load_finite_baseline(box, cache_dir)
    else:
        bdays = required_baseline_days()
        sst_b = loader(box, bdays)
        fields = computed_fields(sst_b, bdays, box)
        fin_b = sea_cells(sst_b)
    if sea is None:
        sea = fin_b & sea_cells(sst_t)
    return detect(sst_t, target_days, box, fields, sea)

