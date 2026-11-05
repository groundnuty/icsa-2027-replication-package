"""Driver: python -m icsa.instances.run boxes | cache | report"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from .. import paths
from ..extent import CellBox
from . import boxes as B, cache, report

OUT = Path(paths.DATA_ROOT) / "instances"
REPO = Path(__file__).resolve().parents[2] / "data" / "instances"
H = W = 60
TOL = 0.005
SOURCE = {"s1_dir": str(paths.S1_DIR), "note": "complete uncompressed S1 (not s1z)"}


def load_boxes() -> list[CellBox]:
    d = json.loads((REPO / "boxes.json").read_text())
    return [CellBox(*b["cells"]) for b in d["boxes"]]


def make_boxes() -> None:
    from .. import grid
    from ..refdet import sea_mask
    from . import eligibility as E
    sea = np.load(OUT / "seascan.npz")["baseline"]
    bal = sea_mask(CellBox(0, grid.NLAT, 0, grid.NLON))
    cls = E.classify(sea, bal)
    r1, r2, _ = E.eligible_mask(cls, H, W)
    sel = B.select(sea, H, W, tol=TOL, allowed=r1 & r2)
    assert sel is not None
    rows = []
    for k, (b, n) in enumerate(zip(sel.boxes, sel.sea)):
        la0, la1, lo0, lo1 = B.bounds(b)
        assert B.cells_in_bounds(la0, la1, lo0, lo1) == b
        sl = (slice(b.lat0, b.lat1), slice(b.lon0, b.lon1))
        assert not cls.inland[sl].any() and (sea & bal)[sl].sum() >= 0.95 * sea[sl].sum()
        rows.append(dict(region_id=f"R{k:02d}", cells=[b.lat0, b.lat1, b.lon0, b.lon1],
                         lat_min=la0, lat_max=la1, lon_min=lo0, lon_max=lo1, sea_cells=n,
                         share_in_balarea=round(float((sea & bal)[sl].sum() / sea[sl].sum()), 4),
                         small_pocket_cells=int(cls.small_lake[sl].sum()), inland_cells=0))
    assert all(a.disjoint(b) for i, a in enumerate(sel.boxes) for b in sel.boxes[:i])
    s = sel.sea
    REPO.mkdir(parents=True, exist_ok=True)
    (REPO / "boxes.json").write_text(json.dumps(dict(
        source=SOURCE, sea_definition="finite on every day of 1991-12-27..2003-01-05 (box selection); "
        "per instance also finite on every target day", eligibility="rule 1: >=95% of the box's finite cells in BALarea; rule 2: no cell of an inland-water component of >=10 cells, pockets of fewer cells stay "
        "(a lake component: 8-connected finite-outside-BALarea component touching neither BALarea nor the grid edge; icsa.instances.eligibility)",
        box_cells=[H, W], tol=TOL, target=sel.target,
        sea_min=min(s), sea_max=max(s), sea_median=float(np.median(s)), boxes=rows), indent=1))
    print("sea min/max/median", min(s), max(s), np.median(s))


def final() -> None:
    import csv
    import dataclasses

    from . import design as D, groundtruth as G, record as RC, required as R
    from .seascan import period_days
    bx = load_boxes()
    scan = report.load_scan()
    counts = {}
    for r in csv.DictReader(open(REPO / "period_table.csv")):
        if r["kind"] == "junaug":
            counts[(int(r["region"]), int(r["year"]))] = int(r["n_events"])
    des = D.design(counts, len(bx))
    import hashlib
    OUT.mkdir(parents=True, exist_ok=True)
    REPO.mkdir(parents=True, exist_ok=True)
    region_sea = {f"R{k:02d}": scan["baseline"][b.lat0:b.lat1, b.lon0:b.lon1] for k, b in enumerate(bx)}
    for k, b in enumerate(bx):        # time-invariance: every Jun-Aug period mask equals the baseline mask
        for y in range(2003, 2023):
            assert np.array_equal(scan[f"junaug_{y}"][b.lat0:b.lat1, b.lon0:b.lon1], region_sea[f"R{k:02d}"])
    np.savez(REPO / "sea_masks.npz", shape=np.array(bx[0].shape),
             **{k: np.packbits(v) for k, v in region_sea.items()})
    sea_sha = hashlib.sha256((REPO / "sea_masks.npz").read_bytes()).hexdigest()
    base = R.baseline_day_indices()   # pooling superset for the cached fields (not the required extent)
    recs, masks = [], {}
    for p in des.picks:
        box = bx[p.region]
        sl = (slice(box.lat0, box.lat1), slice(box.lon0, box.lon1))
        sst_b = cache.load(p.region, base)
        s, e = period_days("junaug", p.year)
        days = R.target_day_indices(s, e)
        sst_t = cache.load(p.region, days)
        sea = G.sea_for(box, sst_b, sst_t)
        assert np.array_equal(sea, scan["baseline"][sl] & scan[f"junaug_{p.year}"][sl])
        # science ruling: sea = finite on every TARGET day; identical to the earlier definition
        assert np.array_equal(np.isfinite(sst_t).all(0), sea), f"{p.instance_id}: sea sets differ"
        # the fields from only the method-required baseline days equal the full-baseline fields on the target DOYs
        from ..refdet import core as _core, computed_fields as _cf
        rb = R.method_baseline_day_indices(s, e)
        assert rb.size == 1452, rb.size
        site_g = _cf(cache.load(p.region, rb), rb, box)
        ff = G.fields_for(box, sst_b)
        di = np.unique(_core.doy366(days))
        assert np.array_equal(site_g.m90[di], ff.m90[di], equal_nan=True) and np.array_equal(site_g.mclim[di], ff.mclim[di], equal_nan=True), p.instance_id
        det = G.reference_truth(box, p.region, days)          # shared path, its own sea rule (sea=None)
        assert not (det.cell_mask & ~sea).any()                # events only on the finiteness-rule cells
        if p.instance_id == "I00":                             # same result with our mask passed explicitly
            assert np.array_equal(det.cell_mask, G.reference_truth(box, p.region, days, sea).cell_mask)
        from .. import grid as _g
        t = G.Truth([(_g.day_date(e.onset), _g.day_date(e.end)) for e in det.events], det.active, det.cell_mask)
        assert len(t.events) == p.events, (p, len(t.events))   # table and recomputation agree
        rec = RC.build_record(int(p.instance_id[1:]), p.region, box, sea, "junaug", p.year, p.pilot, p.calibration)
        rec.events = [(a.isoformat(), b.isoformat()) for a, b in t.events]
        rec.event_free = not t.events
        rec.active_mask = "".join("1" if x else "0" for x in t.active)
        rec.calibration, rec.wan = p.calibration, p.wan
        assert np.array_equal(sea, region_sea[f"R{p.region:02d}"])
        rec.sea_mask = {"file": "sea_masks.npz", "key": f"R{p.region:02d}", "sha256": sea_sha}
        masks[p.instance_id] = t.cell_mask
        recs.append(rec)
        print(p.instance_id, p.region, p.year, p.events, flush=True)
    np.savez_compressed(OUT / "cell_masks.npz", **{k: np.packbits(v) for k, v in masks.items()})
    (REPO / "instances.json").write_text(json.dumps(dict(
        source=SOURCE,
        sea_masks={"file": "sea_masks.npz", "sha256": sea_sha, "shape": list(bx[0].shape),
                   "what": "per region, time-invariant required sea cells (packbits, row-major, True = sea)"},
        cell_masks={"file": str(OUT / "cell_masks.npz"), "sha256": hashlib.sha256((OUT / "cell_masks.npz").read_bytes()).hexdigest(),
                    "what": "ground truth: per instance id, packbits of the per-cell MHW state (target days, h, w) from the reference; not committed (large)"},
        design=dict(kind="junaug", seed=D.SEED, redraws=des.redraws,
                                   draw_order=D.__doc__), instances=[r.to_json() for r in recs]), indent=1))
    with open(REPO / "instances_table.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "region", "year", "events", "event_free", "pilot", "calibration", "wan"])
        for p in des.picks:
            w.writerow([p.instance_id, f"R{p.region:02d}", p.year, p.events, int(p.event_free),
                        int(p.pilot), int(p.calibration), int(p.wan)])
    print("redraws", des.redraws)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "boxes":
        make_boxes()
    elif cmd == "cache":
        cache.build(load_boxes())
    elif cmd == "final":
        final()
    elif cmd == "report":
        bx = load_boxes()
        rows = report.table(bx)
        import csv
        REPO.mkdir(parents=True, exist_ok=True)
        with open(REPO / "period_table.csv", "w", newline="") as f:
            w = csv.DictWriter(f, rows[0].keys(), lineterminator="\n"); w.writeheader(); w.writerows(rows)
        summ = report.summarise(rows, len(bx)); summ["source"] = SOURCE
        (REPO / "period_report.json").write_text(json.dumps(summ, indent=1))
        print(json.dumps({k: v for k, v in summ.items() if k in ("year", "mayseptember", "junaug")
                          for v in [{kk: vv[kk] for kk in ("all_region_years", "seeded_draw_50")} for vv in [summ[k]]]}, indent=1))
