"""The fixed Octave-equivalence criterion (protocol/parameters.md, #4), per block, identically for all.

    uv run python tools/octave/criterion.py <equivalence root> <report.md> <block> [<block> ...]

1 thresholds: m90 and mclim max |Delta| (ours float64 vs Octave's double) <= 1 float32 ulp at the
  field's magnitude (2^-23 * 256 = 3.05e-5 K for 256-512 K).
2 event state: every cell-day whose state differs must be a boundary case, |SST - threshold| <= 1
  float32 ulp, measured against our (the reference's) float64 threshold; the largest distances of the
  flips from both thresholds are reported. A boundary exceedance can change neighbouring cell-days through the 5-day and gap
  rules, so this is tested by attribution: the exceedances at boundary cell-days are set to Octave's
  and our run rules re-run; no differing cell-day may remain. Reported: differing cell-days, how many
  are themselves boundary cell-days, the boundary flips, and what remains after the patch.
3 events: identical, or identical after the boundary patch of 2 (each such case listed).
4 positive control: precision="octave" gives bit-identical fields (uint64 patterns of every non-NaN
  value, NaN at the same positions; NaN payloads reported apart), cell-day states and events.
Octave's output on byte-identical input (run_block.m) is the only expectation.
"""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

from icsa import grid
from icsa.extent import CellBox
from icsa.refdet import Fields, core, detect

ULP_FIELD = 2.0 ** -23 * 256


def events_of(active, t0):
    z = np.diff(np.concatenate([[0], active.astype(np.int8), [0]]))
    return list(zip((np.nonzero(z == 1)[0] + t0).tolist(), (np.nonzero(z == -1)[0] - 1 + t0).tolist()))


def block(root: Path, b: str) -> dict:
    blk = root / b
    h, w, T, first, lat0, lon0, cs, ce, ms, me = (int(v) for v in (blk / "in" / "meta.txt").read_text().split())
    ymd = lambda v: grid.day_index(dt.date(v // 10000, v // 100 % 100, v % 100))
    d0 = ymd(first)
    days = np.arange(d0, d0 + T)
    sst = np.fromfile(blk / "in" / "sst.bin", np.float32).reshape((h, w, T), order="F").transpose(2, 0, 1)
    base = (ymd(cs), ymd(ce))
    tw = np.arange(ymd(ms), ymd(me) + 1)
    rd = lambda name, n3: np.fromfile(blk / "out" / f"{name}.f64", np.float64).reshape((h, w, n3), order="F").transpose(2, 0, 1)
    o90, omc, ots = rd("m90", 366), rd("mclim", 366), rd("mhw_ts", tw.size)
    box = CellBox(lat0, lat0 + h, lon0, lon0 + w)
    sea = np.ones((h, w), bool)
    x = sst[tw - d0]
    fin = np.isfinite(x)
    theirs = np.isfinite(ots)
    ev_o = events_of(theirs.any(axis=(1, 2)), int(tw[0]))
    src = json.loads((blk / "in" / "source.json").read_text())
    r = {"block": b, "box": [lat0, lat0 + h, lon0, lon0 + w], "detection": src["detection"], "source": src["source"],
         "sst_sha256": src["sst_sha256"], "cells_finite": int(np.isfinite(sst).any(0).sum()),
         "cells_intermittent_nan": int((np.isfinite(sst).any(0) & ~np.isfinite(sst).all(0)).sum()),
         "octave_cell_days_in_events": int(theirs.sum()), "octave_events": len(ev_o)}
    # 1
    f64 = core.climatology(sst, days, baseline=base)
    c1 = {}
    for k, (name, ref) in enumerate((("m90", o90), ("mclim", omc))):
        both = np.isfinite(f64[k]) & np.isfinite(ref)
        dd = np.abs(f64[k] - ref)[both]
        c1[name] = {"max_abs": float(dd.max()) if dd.size else 0.0, "n_compared": int(dd.size),
                    "nan_mismatch": int((np.isfinite(f64[k]) != np.isfinite(ref)).sum())}
    r["c1"] = c1
    r["c1_pass"] = all(v["max_abs"] <= ULP_FIELD and v["nan_mismatch"] == 0 for v in c1.values())
    # 2
    det = detect(x, tw, box, Fields(*f64), sea=sea)
    ours = det.cell_mask & fin
    differ = ours != theirs
    doy = core.doy366(tw)
    t64 = f64[0][doy]
    with np.errstate(invalid="ignore"):
        ex_ours = x.astype(np.float64) >= t64
        ex_oct = x >= o90[doy].astype(np.float32)
    ulp = np.spacing(np.abs(x).astype(np.float32)).astype(np.float64)
    with np.errstate(invalid="ignore"):
        dist_ours = np.abs(x.astype(np.float64) - t64) / ulp      # ulps from our (reference) threshold
        dist_oct = np.abs(x.astype(np.float64) - o90[doy]) / ulp  # ulps from Octave's threshold
    boundary = fin & (dist_ours <= 1.0)                          # Gemini review: our threshold only
    flip = ex_ours != ex_oct
    patched = ex_ours.copy()
    patched[flip & boundary] = ex_oct[flip & boundary]
    st_p = core._runs(patched.reshape(tw.size, -1), core.MIN_DURATION, core.MAX_GAP).reshape(x.shape) & fin
    remain = st_p != theirs
    r["c2"] = {"cell_days_differ": int(differ.sum()), "share_differ": float(differ.sum() / max(theirs.sum(), 1)),
               "differ_that_are_boundary_cell_days": int((differ & boundary).sum()),
               "exceedance_flips": int(flip.sum()), "flips_at_boundary": int((flip & boundary).sum()),
               "flips_not_at_boundary": int((flip & ~boundary).sum()),
               "flips_max_ulp_from_our_threshold": float(dist_ours[flip].max()) if flip.any() else 0.0,
               "flips_max_ulp_from_octave_threshold": float(dist_oct[flip].max()) if flip.any() else 0.0,
               "differ_remaining_after_boundary_patch": int(remain.sum())}
    r["c2_pass"] = r["c2"]["flips_not_at_boundary"] == 0 and r["c2"]["differ_remaining_after_boundary_patch"] == 0
    # 3
    ev = [(e.onset, e.end) for e in det.events]
    ev_p = events_of(st_p.any(axis=(1, 2)), int(tw[0]))
    r["c3"] = {"events_identical": ev == ev_o, "events_identical_after_patch": ev_p == ev_o,
               "changed_by_boundary": [] if ev == ev_o else
               [{"ours_only": sorted(set(ev) - set(ev_o)), "octave_only": sorted(set(ev_o) - set(ev))}]}
    r["c3_pass"] = ev == ev_o or ev_p == ev_o
    # 4
    foc = core.climatology(sst, days, baseline=base, precision="octave")
    det_o = detect(x, tw, box, Fields(*foc), sea=sea, precision="octave")
    def bits_equal(a, b):
        """Bit identity: same NaN positions, and identical uint64 patterns on every non-NaN value
        (so +0.0 and -0.0 differ). NaN payloads are reported apart: x86 makes default NaNs with the
        sign bit set, numpy's literal NaN has it clear, and a NaN's payload carries no value."""
        a, b = np.ascontiguousarray(a, np.float64), np.ascontiguousarray(b, np.float64)
        na, nb = np.isnan(a), np.isnan(b)
        return bool(np.array_equal(na, nb) and np.array_equal(a.view(np.uint64)[~na], b.view(np.uint64)[~nb]))

    bit = all(bits_equal(foc[k], ref) for k, ref in enumerate((o90, omc)))
    nan_payload_same = all(np.array_equal(foc[k].view(np.uint64)[np.isnan(foc[k])], ref.view(np.uint64)[np.isnan(ref)])
                           for k, ref in enumerate((o90, omc)))
    r["c4"] = {"fields_bit_identical": bit, "nan_payloads_identical": nan_payload_same, "cell_days_differ": int(((det_o.cell_mask & fin) != theirs).sum()),
               "events_identical": [(e.onset, e.end) for e in det_o.events] == ev_o}
    r["c4_pass"] = bit and r["c4"]["cell_days_differ"] == 0 and r["c4"]["events_identical"]
    return r


def main():
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    rows = [block(root, b) for b in sys.argv[3:]]
    (out.with_suffix(".json")).write_text(json.dumps(rows, indent=1))
    L = ["# Octave equivalence against the fixed criterion (issue #4)", "",
         "The authors' detectc.m runs under GNU Octave 9.2.0 on byte-identical input; the input sha256 is in source.json.",
         "The criterion is in protocol/parameters.md, and this script's docstring states it.",
         "The ulp is float32's, at the field's magnitude: 3.05e-5 K.", "",
         "| block | box | detection | sea / intermittent-NaN cells | 1: m90, mclim max abs diff | 2: differing cell-days (share) / of them boundary / flips at, not at boundary / left after patch | 3: events (Octave) identical / after patch | 4: octave mode bit-identical | pass 1 2 3 4 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        c2 = r["c2"]
        L.append(f"| {r['block']} | {r['box'][0]}:{r['box'][1]}, {r['box'][2]}:{r['box'][3]} | {r['detection'][0]}..{r['detection'][1]} | "
                 f"{r['cells_finite']} / {r['cells_intermittent_nan']} | {r['c1']['m90']['max_abs']:.2e}, {r['c1']['mclim']['max_abs']:.2e} | "
                 f"{c2['cell_days_differ']} ({c2['share_differ']:.1e}) / {c2['differ_that_are_boundary_cell_days']} / "
                 f"{c2['flips_at_boundary']}, {c2['flips_not_at_boundary']} / {c2['differ_remaining_after_boundary_patch']} | "
                 f"{r['octave_events']}: {r['c3']['events_identical']} / {r['c3']['events_identical_after_patch']} | "
                 f"{r['c4']['fields_bit_identical'] and r['c4']['cell_days_differ'] == 0 and r['c4']['events_identical']} | "
                 f"{'Y' if r['c1_pass'] else 'N'} {'Y' if r['c2_pass'] else 'N'} {'Y' if r['c3_pass'] else 'N'} {'Y' if r['c4_pass'] else 'N'} |")
    for r in rows:
        if r["c3"]["changed_by_boundary"]:
            L.append(f"\n{r['block']}: events changed by boundary cell-days: {r['c3']['changed_by_boundary']}")
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
