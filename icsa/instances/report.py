"""Period-length report (#5): reference events per (region, period) for the three
candidate lengths, over every region x year 2003..2022, plus the seeded random draw
of two distinct years per region.

Run after `seascan` (sea masks) and `cache.build` (per-box SST). Writes
<out>/period_table.csv and <out>/period_report.json.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from .. import grid, paths
from ..extent import CellBox
from . import cache, groundtruth as G, required as R
from .seascan import KINDS, period_days

YEARS = list(range(2003, 2023))   # calendar-year candidates come from 2003..2022
DRAW_SEED = 20271


def load_scan() -> dict[str, np.ndarray]:
    with np.load(Path(paths.DATA_ROOT) / "instances" / "seascan.npz") as z:
        return {k: z[k] for k in z.files}


def draw_years(n_regions: int, seed: int = DRAW_SEED) -> list[tuple[int, int]]:
    rng = np.random.default_rng(seed)
    return [tuple(sorted(int(y) for y in rng.choice(YEARS, 2, replace=False))) for _ in range(n_regions)]


def table(boxes: list[CellBox]) -> list[dict]:
    scan = load_scan()
    rows = []
    base_days = R.baseline_day_indices()
    for k, box in enumerate(boxes):
        sl = (slice(box.lat0, box.lat1), slice(box.lon0, box.lon1))
        base_sea = scan["baseline"][sl]
        sst_base = cache.load(k, base_days)
        fields = G.fields_for(box, sst_base)
        assert np.array_equal(np.isfinite(sst_base).all(0), base_sea), "cache and scan disagree"
        for kind in KINDS:
            for y in YEARS:
                s, e = period_days(kind, y)
                days = R.target_day_indices(s, e)
                sst_t = cache.load(k, days)
                sea = base_sea & scan[f"{kind}_{y}"][sl]
                assert np.array_equal(sea, G.sea_for(box, sst_base, sst_t))
                t = G.truth(box, fields, sst_t, days, sea)
                rows.append(dict(region=k, kind=kind, year=y, sea_cells=int(sea.sum()),
                                 n_events=len(t.events), active_days=int(t.active.sum()),
                                 events=";".join(f"{a}..{b}" for a, b in t.events)))
        print("region", k, "done", flush=True)
    return rows


def summarise(rows: list[dict], n_regions: int) -> dict:
    out: dict = {}
    draw = draw_years(n_regions)
    for kind in KINDS:
        allr = [r for r in rows if r["kind"] == kind]
        pick = [r for r in allr if r["year"] in draw[r["region"]]]
        def dist(rs):
            n = np.array([r["n_events"] for r in rs])
            return {"n": len(rs), "event_free": int((n == 0).sum()),
                    "events_hist": {int(v): int((n == v).sum()) for v in np.unique(n)},
                    "mean": float(n.mean()), "median": float(np.median(n)), "max": int(n.max())}
        out[kind] = {"all_region_years": dist(allr), "seeded_draw_50": dist(pick),
                     "event_free_per_year": {y: sum(1 for r in allr if r["year"] == y and r["n_events"] == 0)
                                             for y in YEARS},
                     "region_event_free_years": {k: sum(1 for r in allr if r["region"] == k and r["n_events"] == 0)
                                                 for k in range(n_regions)}}
    out["draw_years"] = draw
    return out
