"""The fixed four-part equivalence criterion (protocol/parameters.md, #4; tools/octave/criterion.py) on the whole domain.

    python3 domain_criterion.py chunks <pack dir> <shards dir> <out dir> [--workers K] [--cols-per-chunk 2] [--only a,b]
    python3 domain_criterion.py report <pack dir> <shards dir> <step3 events.txt> <out dir> <report stem>
    python3 domain_criterion.py selftest <part-1 root> <block>

`chunks` takes the packed S1 cells (pack_domain.py), cuts them into chunks of whole columns of Step_1's 449 x 379
layout, and for each chunk runs the body of `criterion.block` unchanged in its steps:

1 thresholds: m90 and mclim max |Delta| (reference float64 vs Octave's double) <= 1 float32 ulp at the field's
  magnitude (2^-23 * 256 = 3.05e-5 K).
2 event state: raw differing cell-days; the boundary flips (|SST - our threshold| <= 1 float32 ulp); the exceedances at
  boundary cell-days are set to Octave's, the run rules re-applied, and the residual counted.
3 events: the domain event list of the reference, of Octave, and of the patched reference.
4 positive control: precision="octave" gives bit-identical fields, cell-day states and events.

Cells are independent in both programs, so a chunk of cells is a (days, cells, 1) array and the domain event rule ("a day
is active if any cell is in an event with a finite anomaly") is the OR of the chunks' active days. Counts add; max
differences take the max. `report` adds them up, takes Octave's event list from Step_3 as it ran (and checks it against
the one recomputed from the cell-day states), and compares each event list with the published 189 exactly as
`icsa.refdet.validate` does (compare_events: exact onset and end, overlap). `selftest` runs the chunk function on one of
part 1's blocks and checks every number against `criterion.block` on the same files.
"""
import argparse
import collections
import datetime as dt
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools" / "octave"))   # the part-1 tool, in tools/octave of the repo
import criterion  # noqa: E402  (tools/octave/criterion.py, the part-1 tool, unchanged)

from icsa import grid  # noqa: E402
from icsa.extent import CellBox  # noqa: E402
from icsa.refdet import Fields, core, detect  # noqa: E402

ULP_FIELD = criterion.ULP_FIELD
N_CELLS, T_DAYS, ROWS, COLS = 170171, grid.NDAYS, 449, 379
BASE = (grid.day_index(dt.date(1992, 1, 1)), grid.day_index(dt.date(2002, 12, 31)))
TW = np.arange(grid.day_index(dt.date(1982, 1, 2)), grid.day_index(dt.date(2023, 12, 30)) + 1)


def chunk(sst_all, o90, omc, ots, shape, d0=0, base=BASE, tw=TW):
    """One chunk of cells laid out C-order as `shape` = (h, w). sst_all (T, h*w) float32 for global days d0..d0+T-1; o90, omc
    (366, h*w) float64 and ots (len(tw), h*w) float64 are Octave's outputs. Returns (counts dict, actives dict). The steps
    are those of criterion.block."""
    T = sst_all.shape[0]
    h, w = shape
    days = np.arange(d0, d0 + T)
    sst = sst_all.reshape(T, h, w)
    o90, omc, ots = o90.reshape(366, h, w), omc.reshape(366, h, w), ots.reshape(tw.size, h, w)
    box = CellBox(0, h, 0, w)
    sea = np.ones((h, w), bool)
    x = sst[tw - d0]
    fin = np.isfinite(x)
    theirs = np.isfinite(ots)
    r = {"cells": h * w, "octave_cell_days_in_events": int(theirs.sum())}
    # 1
    f64 = core.climatology(sst, days, baseline=base)
    for k, (name, ref) in enumerate((("m90", o90), ("mclim", omc))):
        both = np.isfinite(f64[k]) & np.isfinite(ref)
        dd = np.abs(f64[k] - ref)[both]
        r[f"c1_{name}"] = {"max_abs": float(dd.max()) if dd.size else 0.0, "n_compared": int(dd.size),
                           "n_above_ulp": int((dd > ULP_FIELD).sum()),
                           "nan_mismatch": int((np.isfinite(f64[k]) != np.isfinite(ref)).sum())}
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
        dist_ours = np.abs(x.astype(np.float64) - t64) / ulp
        dist_oct = np.abs(x.astype(np.float64) - o90[doy]) / ulp
    boundary = fin & (dist_ours <= 1.0)
    flip = ex_ours != ex_oct
    patched = ex_ours.copy()
    patched[flip & boundary] = ex_oct[flip & boundary]
    st_p = core._runs(patched.reshape(tw.size, -1), core.MIN_DURATION, core.MAX_GAP).reshape(x.shape) & fin
    remain = st_p != theirs
    r["c2"] = {"cell_days_differ": int(differ.sum()), "differ_that_are_boundary_cell_days": int((differ & boundary).sum()),
               "exceedance_flips": int(flip.sum()), "flips_at_boundary": int((flip & boundary).sum()),
               "flips_not_at_boundary": int((flip & ~boundary).sum()),
               "flips_max_ulp_from_our_threshold": float(dist_ours[flip].max()) if flip.any() else 0.0,
               "flips_max_ulp_from_octave_threshold": float(dist_oct[flip].max()) if flip.any() else 0.0,
               "differ_remaining_after_boundary_patch": int(remain.sum()),
               "reference_cell_days_in_events": int(ours.sum())}
    act = {"ours": det.active, "octave": theirs.any(axis=(1, 2)), "patched": st_p.any(axis=(1, 2))}
    # 4
    foc = core.climatology(sst, days, baseline=base, precision="octave")
    det_o = detect(x, tw, box, Fields(*foc), sea=sea, precision="octave")
    bits = all(criterion_bits_equal(foc[k], ref) for k, ref in enumerate((o90, omc)))
    nan_payload_same = all(np.array_equal(foc[k].view(np.uint64)[np.isnan(foc[k])], ref.view(np.uint64)[np.isnan(ref)])
                           for k, ref in enumerate((o90, omc)))
    r["c4"] = {"fields_bit_identical": bits, "nan_payloads_identical": nan_payload_same,
               "cell_days_differ": int(((det_o.cell_mask & fin) != theirs).sum())}
    act["octave_mode"] = det_o.active
    return r, act


def criterion_bits_equal(a, b):
    a, b = np.ascontiguousarray(a, np.float64), np.ascontiguousarray(b, np.float64)
    na, nb = np.isnan(a), np.isnan(b)
    return bool(np.array_equal(na, nb) and np.array_equal(a.view(np.uint64)[~na], b.view(np.uint64)[~nb]))


# ---------------------------------------------------------------------------------------------- chunks

def read_shards(shards_dir):
    return [(n, int(a), int(b)) for n, a, b in (ln.split() for ln in (Path(shards_dir) / "shards.txt").read_text().splitlines() if ln.strip())]


def work(args):
    pack_dir, shards_dir, out_dir, name, ja, jb, a, b = args       # shard columns ja..jb (1-based), chunk = columns a..b-1 within it (0-based)
    out = Path(out_dir) / f"chunk_{ja + a:03d}_{ja + b - 1:03d}"
    if (out.with_suffix(".json")).exists():
        return str(out), "cached"
    nc = jb - ja + 1
    c0 = (ja - 1 + a) * ROWS
    c1 = (ja - 1 + b) * ROWS
    mm = np.memmap(Path(pack_dir) / "packed.f32", dtype=np.float32, mode="r", shape=(T_DAYS, N_CELLS))
    sst = np.array(mm[:, c0:c1])
    sd = Path(shards_dir) / name
    m90 = np.memmap(sd / "m90.f64", np.float64, "r", shape=(366, nc, ROWS))[:, a:b, :].reshape(366, -1)
    mcl = np.memmap(sd / "mclim.f64", np.float64, "r", shape=(366, nc, ROWS))[:, a:b, :].reshape(366, -1)
    ots = np.memmap(sd / "mhw_ts.f64", np.float64, "r", shape=(TW.size, nc, ROWS))[:, a:b, :].reshape(TW.size, -1)
    t0 = time.time()
    r, act = chunk(sst, np.array(m90), np.array(mcl), np.array(ots), (b - a, ROWS))
    r.update({"shard": name, "cells_first_last": [c0, c1 - 1], "seconds": round(time.time() - t0, 1)})
    np.savez_compressed(out.with_suffix(".npz"), **act)
    out.with_suffix(".json").write_text(json.dumps(r))
    return str(out), f"{r['seconds']}s"


def cmd_chunks(a):
    shards = read_shards(a.shards)
    jobs = []
    for name, ja, jb in shards:
        nc = jb - ja + 1
        for s in range(0, nc, a.cols_per_chunk):
            jobs.append((a.pack, a.shards, a.out, name, ja, jb, s, min(s + a.cols_per_chunk, nc)))
    if a.only:
        keep = set(a.only.split(","))
        jobs = [j for j in jobs if j[3] in keep]
    Path(a.out).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with mp.Pool(a.workers) as pool:
        for i, (o, msg) in enumerate(pool.imap_unordered(work, jobs), 1):
            print(f"{i}/{len(jobs)} {Path(o).name} {msg} elapsed {time.time() - t0:.0f}s", flush=True)


# ---------------------------------------------------------------------------------------------- report

def events_of(active, t0):
    return criterion.events_of(active, t0)


def cmd_report(a):
    out = Path(a.out)
    rows = [json.loads(p.read_text()) for p in sorted(out.glob("chunk_*.json"))]
    acts = [np.load(p) for p in sorted(out.glob("chunk_*.npz"))]
    cells = sum(r["cells"] for r in rows)
    assert cells == N_CELLS, f"chunks cover {cells} of {N_CELLS} cells"
    cover = sorted(tuple(r["cells_first_last"]) for r in rows)
    assert cover[0][0] == 0 and cover[-1][1] == N_CELLS - 1 and all(cover[i][1] + 1 == cover[i + 1][0] for i in range(len(cover) - 1)), "chunks are not contiguous"
    S = lambda path: sum(_get(r, path) for r in rows)
    M = lambda path: max(_get(r, path) for r in rows)
    c1 = {}
    for name in ("m90", "mclim"):
        c1[name] = {"max_abs": M(f"c1_{name}.max_abs"), "n_compared": S(f"c1_{name}.n_compared"),
                    "n_above_ulp": S(f"c1_{name}.n_above_ulp"), "nan_mismatch": S(f"c1_{name}.nan_mismatch")}
    c2 = {k: S(f"c2.{k}") for k in ("cell_days_differ", "differ_that_are_boundary_cell_days", "exceedance_flips", "flips_at_boundary",
                                     "flips_not_at_boundary", "differ_remaining_after_boundary_patch", "reference_cell_days_in_events")}
    c2["flips_max_ulp_from_our_threshold"] = M("c2.flips_max_ulp_from_our_threshold")
    c2["flips_max_ulp_from_octave_threshold"] = M("c2.flips_max_ulp_from_octave_threshold")
    octave_cell_days = S("octave_cell_days_in_events")
    c2["octave_cell_days_in_events"] = octave_cell_days
    c2["share_differ"] = c2["cell_days_differ"] / max(octave_cell_days, 1)
    OR = lambda key: np.any([z[key] for z in acts], axis=0)
    t0 = int(TW[0])
    ev_ours, ev_oct, ev_pat, ev_octmode = (events_of(OR(k), t0) for k in ("ours", "octave", "patched", "octave_mode"))
    step3 = [tuple(map(int, ln.split())) for ln in Path(a.step3).read_text().splitlines() if ln.strip()]
    ev_step3 = [(s - 1 + t0, e - 1 + t0) for s, e in step3]          # Step_3's indices count from mhw_start (1-based)
    c3 = {"events_reference": len(ev_ours), "events_octave_step3": len(ev_step3),
          "step3_equals_events_of_octave_cell_day_states": ev_step3 == ev_oct,
          "events_identical": ev_ours == ev_oct, "events_identical_after_patch": ev_pat == ev_oct,
          "ours_only": sorted(set(ev_ours) - set(ev_oct)), "octave_only": sorted(set(ev_oct) - set(ev_ours)),
          "patched_ours_only": sorted(set(ev_pat) - set(ev_oct)), "patched_octave_only": sorted(set(ev_oct) - set(ev_pat)),
          "active_days_reference": int(OR("ours").sum()), "active_days_octave": int(OR("octave").sum())}
    c4 = {"fields_bit_identical": all(r["c4"]["fields_bit_identical"] for r in rows),
          "nan_payloads_identical": all(r["c4"]["nan_payloads_identical"] for r in rows),
          "cell_days_differ": S("c4.cell_days_differ"), "events_identical": ev_octmode == ev_oct,
          "chunks_bit_identical": f"{sum(r['c4']['fields_bit_identical'] for r in rows)}/{len(rows)}"}
    ok = {"1": all(v["max_abs"] <= ULP_FIELD and v["nan_mismatch"] == 0 for v in c1.values()),
          "2": c2["flips_not_at_boundary"] == 0 and c2["differ_remaining_after_boundary_patch"] == 0,
          "3": ev_ours == ev_oct or ev_pat == ev_oct,
          "4": c4["fields_bit_identical"] and c4["cell_days_differ"] == 0 and c4["events_identical"]}
    # the published catalogue, as icsa.refdet.validate compares it
    from icsa import paths
    from icsa.refdet import validate as V
    cat = V.parse_catalogue(paths.REF / "bashiri" / "data" / "BALMHW_data_info.csv")
    E = collections.namedtuple("E", "onset end")
    published = {k: V.compare_events(cat, [E(*e) for e in ev]) for k, ev in
                 (("octave_authors_code", ev_step3), ("reference_computed_float64", ev_ours), ("reference_octave_mode", ev_octmode))}
    rec = {"cells": cells, "chunks": len(rows), "days_detection": [str(grid.day_date(int(TW[0]))), str(grid.day_date(int(TW[-1])))],
           "ulp_field": ULP_FIELD, "criterion_pass": ok, "c1": c1, "c2": c2, "c3": c3, "c4": c4,
           "events": {"reference": ev_ours, "octave": ev_oct, "patched": ev_pat},
           "published_189": published, "compute_seconds_numpy": round(sum(r["seconds"] for r in rows))}
    Path(a.stem).with_suffix(".json").write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps({k: rec[k] for k in ("cells", "chunks", "criterion_pass", "c1", "c2", "c4")}, indent=1))
    print(json.dumps({k: v for k, v in c3.items()}, default=str)[:3000])
    for k, v in published.items():
        print(k, {x: v[x] for x in ("published", "ours", "exact_matches", "published_overlapped", "ours_overlapping_none")})


def _get(d, path):
    for k in path.split("."):
        d = d[k]
    return d


# ---------------------------------------------------------------------------------------------- selftest

def cmd_selftest(a):
    """Run `chunk` on one part-1 block and compare with criterion.block on the same files (the numbers must agree)."""
    root, b = Path(a.root), a.block
    h, w, T, first, lat0, lon0, cs, ce, ms, me = (int(v) for v in (root / b / "in" / "meta.txt").read_text().split())
    ymd = lambda v: grid.day_index(dt.date(v // 10000, v // 100 % 100, v % 100))
    d0 = ymd(first)
    base, tw = (ymd(cs), ymd(ce)), np.arange(ymd(ms), ymd(me) + 1)
    sst = np.fromfile(root / b / "in" / "sst.bin", np.float32).reshape((h, w, T), order="F").transpose(2, 0, 1).reshape(T, h * w)
    rd = lambda name, n3: np.fromfile(root / b / "out" / f"{name}.f64", np.float64).reshape((h, w, n3), order="F").transpose(2, 0, 1).reshape(n3, h * w)
    r, act = chunk(sst, rd("m90", 366), rd("mclim", 366), rd("mhw_ts", tw.size), (h, w), d0=d0, base=base, tw=tw)
    ref = criterion.block(root, b)
    cmp = {"c1_max_abs_m90": (r["c1_m90"]["max_abs"], ref["c1"]["m90"]["max_abs"]), "c1_max_abs_mclim": (r["c1_mclim"]["max_abs"], ref["c1"]["mclim"]["max_abs"]),
           "c2_differ": (r["c2"]["cell_days_differ"], ref["c2"]["cell_days_differ"]),
           "c2_boundary": (r["c2"]["differ_that_are_boundary_cell_days"], ref["c2"]["differ_that_are_boundary_cell_days"]),
           "c2_flips": (r["c2"]["exceedance_flips"], ref["c2"]["exceedance_flips"]),
           "c2_flips_at": (r["c2"]["flips_at_boundary"], ref["c2"]["flips_at_boundary"]),
           "c2_flips_not_at": (r["c2"]["flips_not_at_boundary"], ref["c2"]["flips_not_at_boundary"]),
           "c2_remaining": (r["c2"]["differ_remaining_after_boundary_patch"], ref["c2"]["differ_remaining_after_boundary_patch"]),
           "c2_max_ulp_ours": (r["c2"]["flips_max_ulp_from_our_threshold"], ref["c2"]["flips_max_ulp_from_our_threshold"]),
           "c2_max_ulp_oct": (r["c2"]["flips_max_ulp_from_octave_threshold"], ref["c2"]["flips_max_ulp_from_octave_threshold"]),
           "c4_bits": (r["c4"]["fields_bit_identical"], ref["c4"]["fields_bit_identical"]),
           "c4_differ": (r["c4"]["cell_days_differ"], ref["c4"]["cell_days_differ"]),
           "octave_cell_days": (r["octave_cell_days_in_events"], ref["octave_cell_days_in_events"])}
    t0 = int(tw[0])
    ev_oct, ev_ours, ev_pat, ev_om = (events_of(act[k], t0) for k in ("octave", "ours", "patched", "octave_mode"))
    cmp["c3_identical"] = (ev_ours == ev_oct, ref["c3"]["events_identical"])
    cmp["c3_identical_after_patch"] = (ev_pat == ev_oct, ref["c3"]["events_identical_after_patch"])
    cmp["c4_events"] = (ev_om == ev_oct, ref["c4"]["events_identical"])
    bad = {k: v for k, v in cmp.items() if v[0] != v[1]}
    print(json.dumps(cmp, indent=1, default=str))
    print("SELFTEST", "FAIL " + json.dumps(bad, default=str) if bad else "PASS: every number equals criterion.block's")
    sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("chunks")
    c.add_argument("pack"); c.add_argument("shards"); c.add_argument("out")
    c.add_argument("--workers", type=int, default=8); c.add_argument("--cols-per-chunk", type=int, default=2); c.add_argument("--only")
    r = sub.add_parser("report")
    r.add_argument("pack"); r.add_argument("shards"); r.add_argument("step3"); r.add_argument("out"); r.add_argument("stem")
    s = sub.add_parser("selftest")
    s.add_argument("root"); s.add_argument("block")
    a = ap.parse_args()
    {"chunks": cmd_chunks, "report": cmd_report, "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    main()
