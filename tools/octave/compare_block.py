"""Compare our detector with the authors' detectc.m run under Octave on the same block (issue #4).

    uv run python tools/octave/compare_block.py <block dir>      # reads <block>/in, <block>/out, writes <block>/out/compare.json

The only expectation is Octave's output on identical input (run_block.m): m90/mclim in the precision
detectc holds them (double), and mhw_ts (finite = cell-day in an event, as Step_3/4 read it).
Reported:
  fields     ours (float64, and precision="octave") vs Octave: max abs diff, cell-doys that differ
  cells      cell-day event state, three ways: (i) ours float64 end to end, (ii) ours with
             precision="octave", (iii) Octave's own fields through our detection (isolates the run rules)
  flips      for (i): every cell-day whose raw exceedance differs from Octave's, with |sst - m90| in
             float32 ulps (a precision flip is within 1 ulp of the threshold)
  domain     active days and events of the block (Step_3 rule: a day is active if any cell has a
             finite mhw_ts)
  estimators every candidate percentile estimator against Octave's m90 (the code-level oracle)
"""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

from icsa import grid
from icsa.extent import CellBox
from icsa.refdet import Fields, core, detect
from icsa.refdet.validate import CAND_ESTIMATORS

blk = Path(sys.argv[1])
h, w, T, first, lat0, lon0, cs, ce, ms, me = (int(v) for v in (blk / "in" / "meta.txt").read_text().split())
ymd = lambda v: grid.day_index(dt.date(v // 10000, v // 100 % 100, v % 100))
d0 = ymd(first)
days = np.arange(d0, d0 + T)
sst = np.fromfile(blk / "in" / "sst.bin", np.float32).reshape((h, w, T), order="F").transpose(2, 0, 1)
base = (ymd(cs), ymd(ce))
tw = np.arange(ymd(ms), ymd(me) + 1)
rd = lambda name, n3: np.fromfile(blk / "out" / f"{name}.f64", np.float64).reshape((h, w, n3), order="F").transpose(2, 0, 1)
o90, omc = rd("m90", 366), rd("mclim", 366)
ots = rd("mhw_ts", tw.size)
box = CellBox(lat0, lat0 + h, lon0, lon0 + w)
sea = np.ones((h, w), bool)          # Octave runs every cell of the block; all-NaN cells are skipped by both
x = sst[tw - d0]
fin = np.isfinite(sst)
res = {"block": str(blk), "box": [lat0, lat0 + h, lon0, lon0 + w], "baseline": base, "detection": [int(tw[0]), int(tw[-1])],
       "cells_finite": int(fin.any(0).sum()), "cells_intermittent_nan": int((fin.any(0) & ~fin.all(0)).sum())}


def field_cmp(a, b):
    fa, fb = np.isfinite(a), np.isfinite(b)
    both = fa & fb
    d = np.abs(a - b)[both]
    return {"finite_ours": int(fa.sum()), "finite_octave": int(fb.sum()), "nan_mismatch": int((fa != fb).sum()),
            "max_abs": float(d.max()) if d.size else 0.0, "n_differ": int((d != 0).sum()),
            "n_differ_gt_1e-9": int((d > 1e-9).sum())}


def runs_of(a):
    z = np.diff(np.concatenate([[0], a.astype(np.int8), [0]]))
    return list(zip((np.nonzero(z == 1)[0] + tw[0]).tolist(), (np.nonzero(z == -1)[0] - 1 + tw[0]).tolist()))


f64 = core.climatology(sst, days, baseline=base)
foc = core.climatology(sst, days, baseline=base, precision="octave")
res["fields"] = {f"{name}_{lab}": field_cmp(ours[k], theirs)
                 for lab, ours in (("float64", f64), ("octave", foc))
                 for k, (name, theirs) in enumerate((("m90", o90), ("mclim", omc)))}

theirs = np.isfinite(ots)
act_o = theirs.any(axis=(1, 2))
ev_o = runs_of(act_o)
res["octave"] = {"cell_days_in_events": int(theirs.sum()), "active_days": int(act_o.sum()), "events": len(ev_o)}
cases = {"float64": (Fields(*f64), "float64"), "octave_emulation": (Fields(*foc), "octave"),
         "octave_fields": (Fields(o90, omc), "octave")}
res["cells"] = {}
for lab, (fl, prec) in cases.items():
    det = detect(x, tw, box, fl, sea=sea, precision=prec)
    ours = det.cell_mask & np.isfinite(x)
    ev = [(e.onset, e.end) for e in det.events]
    res["cells"][lab] = {"cell_days_in_events": int(ours.sum()), "cell_days_differ": int((ours != theirs).sum()),
                         "active_days_differ": int((det.active != act_o).sum()),
                         "events": len(ev), "events_identical": ev == ev_o}

# raw exceedance: our float64 comparison vs Octave's (single(sst) >= single(m90_octave))
doy = core.doy366(tw)
t64 = f64[0][doy]
with np.errstate(invalid="ignore"):
    ex_ours = x.astype(np.float64) >= t64
    ex_oct = x >= o90[doy].astype(np.float32)
flip = ex_ours != ex_oct
ulp = np.spacing(np.abs(x[flip]).astype(np.float32)).astype(np.float64)
dist = np.abs(x[flip].astype(np.float64) - t64[flip]) / ulp
res["flips"] = {"exceedance_flips": int(flip.sum()), "max_distance_ulp": float(dist.max()) if dist.size else 0.0,
                "distances_ulp": sorted(float(v) for v in dist)[:50]}

est = {}
for name in CAND_ESTIMATORS:
    m, _ = core.climatology(sst, days, baseline=base, estimator=name)
    both = np.isfinite(m) & np.isfinite(o90)
    d = np.abs(m - o90)[both]
    est[name] = {"max_abs": float(d.max()) if d.size else 0.0, "mean_abs": float(d.mean()) if d.size else 0.0}
res["estimators_vs_octave_m90"] = dict(sorted(est.items(), key=lambda kv: kv[1]["mean_abs"]))
(blk / "out" / "compare.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k != "estimators_vs_octave_m90"}))
print("estimators (mean abs vs Octave m90):", {k: f"{v['mean_abs']:.2e}" for k, v in res["estimators_vs_octave_m90"].items()})
