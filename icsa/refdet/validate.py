"""Validation of the reference detector against the published Baltic MHW catalogue
(Bashiri et al. 2025). Pilot criterion (i) of issue #4.

    uv run python -m icsa.refdet.validate --stage all --workers 6 --out reports/refdet

Ground truth is only the published material under `paths.REF/bashiri/data`: the 189 events in
BALMHW_data_info.csv, the daily maps in BALMHW_event_NNN.nc (finite and non-zero = MHW) and
the fields in BALMHW_supp.nc. Nothing produced by this code is used as an expectation.

Stages
  fields  mode (b) m90/mclim from the baseline years vs the published fields, plus every
          percentile estimator candidate against the published m90 (needs 1991-12-27..2003-01-05)
  events  modes (a) and (b) over all years vs the 189 events and the daily maps (needs all years)
  all     both

SST is read from the raw yearly files (`paths.RAW`) band by band (latitude rows), so the 40 GB
product never sits in memory. Bands run in parallel.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import json
import multiprocessing as mp
import time
from pathlib import Path

import netCDF4
import numpy as np

from .. import grid, paths
from ..extent import CellBox
from . import Fields, baseline_days, core, detect, domain_window, sea_mask
from . import data as rdata

BAND_ROWS = 16
CAND_ESTIMATORS = [  # numpy method names, probed against the published m90
    "hazen", "weibull", "linear", "median_unbiased", "normal_unbiased",
    "inverted_cdf", "averaged_inverted_cdf", "closest_observation", "interpolated_inverted_cdf",
    "lower", "higher", "midpoint", "nearest",
]
PAD = core.HALF_WINDOW


# ----------------------------------------------------------------------------- raw SST by band

def raw_index(raw_dir: Path) -> dict[int, tuple[Path, int]]:
    """Global day index -> (file, time index) for every day in the yearly raw files."""
    out: dict[int, tuple[Path, int]] = {}
    for p in sorted(raw_dir.glob("SST_BAL_*.nc")):
        if "partial" in p.name:
            continue
        try:
            with netCDF4.Dataset(p) as ds:
                t = ds["time"]
                dates = netCDF4.num2date(t[:], t.units, only_use_cftime_datetimes=False,
                                         only_use_python_datetimes=True)
        except OSError:
            continue  # still being written
        for k, dd in enumerate(dates):
            out[(dt.date(dd.year, dd.month, dd.day) - grid.DAY0).days] = (p, k)
    return out


VALID_RANGE = True  # False: only _FillValue is masked, as MATLAB ncread does (diagnostic, --no-valid-range)
ESTIMATORS = True   # False: skip the (slow) estimator sweep against the published m90 (--no-estimators)


def _decode(v, lo: int, hi: int, r0: int, r1: int) -> np.ndarray:
    if VALID_RANGE:
        return np.ma.filled(v[lo:hi + 1, r0:r1, :], np.nan)
    v.set_auto_maskandscale(False)
    raw = v[lo:hi + 1, r0:r1, :]
    out = raw.astype(np.float64) * float(v.scale_factor) + float(v.add_offset)
    out[raw == v._FillValue] = np.nan
    v.set_auto_maskandscale(True)
    return out


def read_band(index: dict[int, tuple[Path, int]], days: np.ndarray, r0: int, r1: int) -> np.ndarray:
    """float32 SST (len(days), r1-r0, NLON), NaN where masked (fill and outside valid_min/max), for `days`."""
    out = np.full((days.size, r1 - r0, grid.NLON), np.nan, np.float32)
    by_file: dict[Path, list[tuple[int, int]]] = {}
    for pos, dday in enumerate(days):
        p, k = index[int(dday)]
        by_file.setdefault(p, []).append((pos, k))
    for p, items in by_file.items():
        with netCDF4.Dataset(p) as ds:
            v = ds["analysed_sst"]
            ks = [k for _, k in items]
            lo, hi = min(ks), max(ks)
            a = _decode(v, lo, hi, r0, r1)
            for pos, k in items:
                out[pos] = a[k - lo]
    return out


# ----------------------------------------------------------------------------- band worker

def _hist_edges() -> np.ndarray:
    return np.concatenate([[0.0], np.logspace(-7, 1, 33)])


def _work(args):
    r0, r1, stage, index, published_ok = args
    box = CellBox(r0, r1, 0, grid.NLON)
    sea = sea_mask(box)
    res: dict = {"r0": r0, "r1": r1}
    b0, b1 = baseline_days()
    w0, w1 = domain_window()
    pub = rdata.published_arrays(box) if published_ok else None
    if stage in ("fields", "all"):
        bdays = np.arange(b0 - PAD, b1 + PAD + 1)
        sst = read_band(index, bdays, r0, r1)
        f = core.climatology(sst, bdays, baseline=(b0, b1))
        fb = Fields(*f)  # float64, as the reference computes
        res["fields_b"] = fb
        if pub is not None:
            res["fieldstats"] = field_stats(fb, pub, sea)
            if ESTIMATORS:
                res["estimators"] = estimator_stats(sst, bdays, (b0, b1), pub[0], sea)
        del sst
    if stage in ("events", "all"):
        days = np.arange(w0 - 1, w1 + 2)  # whole product 1982-01-01..2023-12-31
        sst = read_band(index, days, r0, r1)
        sst = sst[1:-1]  # the detection window; detectc is handed 1982-01-02..2023-12-30 only
        dwin = days[1:-1]
        fb = res.get("fields_b")
        if fb is None:
            bdays = np.arange(b0 - PAD, b1 + PAD + 1)
            f = core.climatology(sst_for(index, bdays, r0, r1), bdays, baseline=(b0, b1))
            fb = Fields(*f)  # float64, as the reference computes
        modes = {"b": fb}
        if pub is not None:
            modes["a"] = Fields(*pub)
        for m, fields in modes.items():
            det = detect(sst, dwin, box, fields, sea)
            res[f"active_{m}"] = det.active
            res[f"cells_{m}"] = np.packbits(det.cell_mask & np.isfinite(sst), axis=2)
            del det
        del sst
    return res


def sst_for(index, days, r0, r1):
    return read_band(index, days, r0, r1)


def field_stats(fb: Fields, pub, sea: np.ndarray) -> dict:
    out = {}
    for name, ours, theirs in (("m90", fb.m90, pub[0]), ("mclim", fb.mclim, pub[1])):
        both = np.isfinite(ours) & np.isfinite(theirs)
        diff = np.abs(ours.astype(np.float64) - theirs.astype(np.float64))[both]
        edges = _hist_edges()
        out[name] = {
            "n": int(diff.size), "max": float(diff.max()) if diff.size else 0.0,
            "sum": float(diff.sum()), "hist": np.histogram(diff, edges)[0].tolist(),
            "nan_only_ours": int((~np.isfinite(ours) & np.isfinite(theirs)).sum()),
            "nan_only_published": int((np.isfinite(ours) & ~np.isfinite(theirs)).sum()),
            "sea_cells_nan_published": int((~np.isfinite(theirs[0]) & sea).sum()),
            "published_finite_not_sea": int((np.isfinite(theirs[0]) & ~sea).sum()),
        }
        cells = np.isfinite(ours).all(0) & np.isfinite(theirs).all(0) & sea
        cmax = np.abs(ours.astype(np.float64) - theirs.astype(np.float64)).max(axis=0)
        out[name]["cells_compared"] = int(cells.sum())
        out[name]["cells_max_doy_gt_0.01"] = int((cells & (cmax > 0.01)).sum())
        out[name]["cells_max_doy_gt_0.1"] = int((cells & (cmax > 0.1)).sum())
        if diff.size:
            idx = np.argwhere(both)[int(np.argmax(diff))]
            out[name]["argmax_doy_row_col"] = [int(idx[0]), int(idx[1]), int(idx[2])]
    return out


def estimator_stats(sst, days, baseline, pub_m90, sea) -> dict:
    """Full pipeline (pooling, smoothing) per candidate estimator, on a sample of sea cells."""
    cols = np.nonzero(sea.any(axis=0))[0][::9]
    out = {}
    cands = [("matlab_formula", None)] + [(n, n) for n in CAND_ESTIMATORS]
    sub = sst[:, :, cols]
    for name, est in cands:
        m90, _ = core.climatology(sub, days, baseline=baseline, estimator=est)
        ref = pub_m90[:, :, cols].astype(np.float64)
        ok = np.isfinite(m90) & np.isfinite(ref) & sea[:, cols][None]
        d = np.abs(m90 - ref)[ok]
        out[name] = {"n": int(d.size), "max": float(d.max()) if d.size else 0.0, "sum": float(d.sum())}
    return out


# ----------------------------------------------------------------------------- comparison

def parse_catalogue(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            on = dt.datetime.strptime(r["event_onset"].strip(), "%Y %b %d").date()
            en = dt.datetime.strptime(r["event_end"].strip(), "%Y %b %d").date()
            rows.append({"file": r["file_name"].strip(), "duration": int(r["event_duration"]),
                         "onset": grid.day_index(on), "end": grid.day_index(en)})
    return rows


def compare_events(published: list[dict], events) -> dict:
    ours = [(e.onset, e.end) for e in events]
    pub = [(p["onset"], p["end"]) for p in published]
    sp, so = set(pub), set(ours)
    return {
        "published": len(pub), "ours": len(ours), "exact_matches": len(sp & so),
        "only_published": [(grid.day_date(a).isoformat(), grid.day_date(b).isoformat()) for a, b in sorted(sp - so)],
        "only_ours": [(grid.day_date(a).isoformat(), grid.day_date(b).isoformat()) for a, b in sorted(so - sp)],
        "durations_consistent": all(p["duration"] == p["end"] - p["onset"] + 1 for p in published),
        **overlap_agreement(pub, ours),
    }


def overlap_agreement(pub: list[tuple[int, int]], ours: list[tuple[int, int]]) -> dict:
    """Event-level agreement beyond exact dates: published events overlapped by at least one of ours,
    ours overlapping none of the published, and the onset/end offsets (ours - published, days) of
    each published event against the overlapping event of ours with the largest overlap."""
    def ov(a, b):
        return min(a[1], b[1]) - max(a[0], b[0]) + 1
    hit, d_on, d_end, merged = 0, [], [], 0
    for p in pub:
        cand = [(ov(p, o), o) for o in ours if ov(p, o) > 0]
        if cand:
            hit += 1
            merged += len(cand) > 1
            o = max(cand)[1]
            d_on.append(o[0] - p[0])
            d_end.append(o[1] - p[1])
    spur = sum(1 for o in ours if not any(ov(p, o) > 0 for p in pub))
    hist = lambda v: {str(k): int(c) for k, c in zip(*np.unique(np.clip(v, -10, 10), return_counts=True))} if v else {}
    return {"published_overlapped": hit, "published_overlapped_by_several": merged, "ours_overlapping_none": spur,
            "onset_offset_hist_clip10": hist(d_on), "end_offset_hist_clip10": hist(d_end)}


def read_event_map(path: Path) -> tuple[np.ndarray, np.ndarray, int]:
    """(days, bool (n, 626, 1051), number of finite exact zeros): MHW = finite (detectc writes
    NaN outside events; the issue's finite-and-non-zero reading differs only if zeros occur,
    which is counted). Day from the time axis."""
    with netCDF4.Dataset(path) as ds:
        m = np.ma.filled(ds["MHW_int_maps"][:], np.nan)
        t = ds["time"]
        dates = netCDF4.num2date(t[:], t.units, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
    days = np.array([(dt.date(x.year, x.month, x.day) - grid.DAY0).days for x in dates])
    return days, np.isfinite(m), int((m == 0).sum())


def map_agreement(published: list[dict], ours_packed: dict[str, np.ndarray], w0: int, data_dir: Path,
                  domain: np.ndarray | None = None) -> list[dict]:
    """Per event and mode: published map vs ours over the event's days (ours = state & finite).
    `domain` (bool (NLAT, NLON)), if given, restricts both maps to those cells."""
    rows = []
    for p in published:
        f = data_dir / p["file"]
        if not f.exists():
            rows.append({"file": p["file"], "missing": True})
            continue
        try:
            days, pm, nzero = read_event_map(f)
        except OSError as e:
            rows.append({"file": p["file"], "unreadable": str(e)})
            continue
        row = {"file": p["file"], "n_days": int(days.size), "days_ok": bool(days[0] == p["onset"] and days[-1] == p["end"]),
               "finite_zeros": nzero}
        if domain is not None:
            pm = pm & domain
        for m, packed in ours_packed.items():
            om = np.unpackbits(packed[days - w0], axis=2, count=grid.NLON).astype(bool)
            if domain is not None:
                om &= domain
            both = int((pm & om).sum())
            only_p = int((pm & ~om).sum())
            only_o = int((~pm & om).sum())
            row[m] = {"both": both, "only_published": only_p, "only_ours": only_o,
                      "jaccard": both / max(both + only_p + only_o, 1),
                      "days_exact": int(((pm == om).all(axis=(1, 2))).sum())}
        rows.append(row)
    return rows


# ----------------------------------------------------------------------------- driver

def assemble(results: list[dict], key: str, axis: int) -> np.ndarray:
    results = sorted(results, key=lambda r: r["r0"])
    return np.concatenate([r[key] for r in results], axis=axis)


def summarize_fields(results: list[dict]) -> dict:
    out = {"m90": {}, "mclim": {}}
    edges = _hist_edges()
    for name in out:
        stats = [r["fieldstats"][name] for r in results if "fieldstats" in r]
        if not stats:
            continue
        n = sum(s["n"] for s in stats)
        hist = np.sum([s["hist"] for s in stats], axis=0)
        cum = np.cumsum(hist) / max(n, 1)
        q = ({f"p{int(100 * p)}": float(edges[1:][min(int(np.searchsorted(cum, p)), edges.size - 2)])
              for p in (0.5, 0.9, 0.99, 0.999, 0.9999)} if n else {})
        out[name] = {
            "n_cells_x_days": n, "max_abs_diff": max(s["max"] for s in stats),
            "mean_abs_diff": sum(s["sum"] for s in stats) / max(n, 1),
            "quantile_upper_bounds_(bin_edges)": q,
            "hist_edges": edges.tolist(), "hist": hist.tolist(),
            "nan_only_ours": sum(s["nan_only_ours"] for s in stats),
            "nan_only_published": sum(s["nan_only_published"] for s in stats),
            "published_finite_cells_not_in_sea_mask": sum(s["published_finite_not_sea"] for s in stats),
            "cells_compared": sum(s.get("cells_compared", 0) for s in stats),
            "cells_max_doy_gt_0.01": sum(s.get("cells_max_doy_gt_0.01", 0) for s in stats),
            "cells_max_doy_gt_0.1": sum(s.get("cells_max_doy_gt_0.1", 0) for s in stats),
        }
    ests = [r["estimators"] for r in results if "estimators" in r]
    if ests:
        out["estimators"] = {
            k: {"max_abs": max(e[k]["max"] for e in ests),
                "mean_abs": sum(e[k]["sum"] for e in ests) / max(sum(e[k]["n"] for e in ests), 1)}
            for k in ests[0]}
    return out


def write_report(out: Path, summary: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "validation.json").write_text(json.dumps(summary, indent=1, default=str))
    L = ["# Reference detector validation (issue #4)", "", f"Run: {summary['run']['started']}, "
         f"raw SST product version/time: {summary['run'].get('product', '?')}", ""]
    f = summary.get("fields")
    if f and f.get("m90"):
        L += ["## Mode (b) fields vs published m90 / mclim", ""]
        for n in ("m90", "mclim"):
            s = f[n]
            L += [f"- {n}: max abs diff {s['max_abs_diff']:.3e} K, mean {s['mean_abs_diff']:.3e} K over "
                  f"{s['n_cells_x_days']} cell-days; upper bounds of diff quantiles {s['quantile_upper_bounds_(bin_edges)']}; "
                  f"NaN only ours {s['nan_only_ours']}, NaN only published {s['nan_only_published']}, "
                  f"published-finite cells outside our sea mask {s['published_finite_cells_not_in_sea_mask']}; "
                  f"cells (finite on every day of year in both) with max abs diff > 0.01 K: "
                  f"{s.get('cells_max_doy_gt_0.01', '?')} of {s.get('cells_compared', '?')}, > 0.1 K: {s.get('cells_max_doy_gt_0.1', '?')}"]
        if "estimators" in f:
            L += ["", "## Percentile estimator candidates (full pipeline, sample of sea cells), diff vs published m90", "",
                  "| estimator | max abs | mean abs |", "|---|---|---|"]
            for k, v in sorted(f["estimators"].items(), key=lambda kv: kv[1]["mean_abs"]):
                L.append(f"| {k} | {v['max_abs']:.3e} | {v['mean_abs']:.3e} |")
        L.append("")
    for m in ("a", "b"):
        e = summary.get("events", {}).get(m)
        if e:
            L += [f"## Mode ({m}) events vs the 189 published", "",
                  f"- published {e['published']}, ours {e['ours']}, exact onset+end matches {e['exact_matches']}",
                  f"- event level: published overlapped by ours {e.get('published_overlapped')}, by several of ours "
                  f"{e.get('published_overlapped_by_several')}; ours overlapping no published {e.get('ours_overlapping_none')}",
                  f"- onset offset (ours - published, days, clipped to 10): {e.get('onset_offset_hist_clip10')}",
                  f"- end offset: {e.get('end_offset_hist_clip10')}",
                  f"- only published: {e['only_published'][:20]}", f"- only ours: {e['only_ours'][:20]}", ""]
    mp_ = summary.get("maps")
    if mp_:
        for m in ("a", "b"):
            rows = [r for r in mp_ if m in r]
            if rows:
                j = np.array([r[m]["jaccard"] for r in rows])
                L += [f"## Mode ({m}) daily maps per event", "",
                      f"- events compared {len(rows)} of {len(mp_)}; jaccard min {j.min():.6f}, mean {j.mean():.6f}; "
                      f"perfect {int((j == 1).sum())}; total only-published cells {sum(r[m]['only_published'] for r in rows)}, "
                      f"only-ours cells {sum(r[m]['only_ours'] for r in rows)}; finite exact-zero map values {sum(r['finite_zeros'] for r in rows)}", ""]
    (out / "validation.md").write_text("\n".join(L))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["fields", "events", "all"], default="all")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default="reports/refdet")
    ap.add_argument("--band-rows", type=int, default=BAND_ROWS)
    ap.add_argument("--no-valid-range", action="store_true",
                    help="mask only _FillValue (not valid_min/max): what MATLAB ncread does")
    ap.add_argument("--max-bands", type=int, default=0, help="only the first N bands (smoke test)")
    ap.add_argument("--no-estimators", action="store_true", help="skip the estimator sweep against the published m90")
    ap.add_argument("--mask-dir", default="", help="save the packed per-cell masks and active days here (.npy), "
                    "so the daily-map comparison can be redone with --maps-from")
    ap.add_argument("--maps-from", default="", help="only redo the daily-map comparison from masks saved with --mask-dir")
    ap.add_argument("--common-domain", action="store_true", help="with --maps-from: restrict both maps to the cells "
                    "where the published m90 is finite (the authors' effective domain)")
    ap.add_argument("--events-from", default="", help="only redo the domain event rule from masks saved with --mask-dir, "
                    "on BALarea and on the authors' effective domain (cells where the published m90 is finite)")
    a = ap.parse_args(argv)
    global VALID_RANGE, ESTIMATORS
    VALID_RANGE = not a.no_valid_range
    ESTIMATORS = not a.no_estimators
    if a.maps_from:
        return maps_only(Path(a.maps_from), Path(a.out), a.common_domain)
    if a.events_from:
        return events_by_domain(Path(a.events_from), Path(a.out))
    t0 = time.time()
    data_dir = paths.REF / "bashiri" / "data"
    index = raw_index(paths.RAW)
    b0, b1 = baseline_days()
    need = list(range(b0 - PAD, b1 + PAD + 1)) if a.stage == "fields" else list(range(grid.NDAYS))
    missing = [d for d in need if d not in index]
    if missing:
        print(f"SST not complete for stage {a.stage}: {len(missing)} days missing "
              f"(first {grid.day_date(missing[0])}); run again when the download has finished")
        return 2
    published_ok = (data_dir / rdata.SUPP_NAME).exists()
    if not published_ok:
        print("BALMHW_supp.nc not present: published-fields comparisons and mode (a) are skipped")
    bands = [(r, min(r + a.band_rows, grid.NLAT)) for r in range(0, grid.NLAT, a.band_rows)]
    if a.max_bands:
        bands = bands[:a.max_bands]
    jobs = [(r0, r1, a.stage, index, published_ok) for r0, r1 in bands]
    with mp.get_context("fork").Pool(a.workers) as pool:
        results = []
        for k, r in enumerate(pool.imap_unordered(_work, jobs)):
            results.append(r)
            print(f"band {r['r0']}-{r['r1']} done ({k + 1}/{len(jobs)}, {time.time() - t0:.0f}s)", flush=True)
    some = next(iter(index.values()))[0]
    with netCDF4.Dataset(some) as ds:
        product = f"{ds.getncattr('product_version')}, created {ds.getncattr('date_created')}"
    summary: dict = {"run": {"started": dt.datetime.now().isoformat(timespec="seconds"), "stage": a.stage,
                             "bands": len(bands), "product": product, "seconds": None}}
    if a.stage in ("fields", "all"):
        summary["fields"] = summarize_fields(results)
    if a.stage in ("events", "all") and not a.max_bands:
        w0, _ = domain_window()
        cat = parse_catalogue(data_dir / "BALMHW_data_info.csv")
        det_days = np.arange(w0, domain_window()[1] + 1)
        summary["events"] = {}
        packed = {}
        for m in ("a", "b"):
            if f"active_{m}" not in results[0]:
                continue
            active = np.logical_or.reduce([r[f"active_{m}"] for r in results])
            ev = core_events(det_days, active)
            summary["events"][m] = compare_events(cat, ev)
            packed[m] = assemble(results, f"cells_{m}", 1)
            if a.mask_dir:
                Path(a.mask_dir).mkdir(parents=True, exist_ok=True)
                np.save(Path(a.mask_dir) / f"cells_{m}.npy", packed[m])
                np.save(Path(a.mask_dir) / f"active_{m}.npy", active)
        summary["maps"] = map_agreement(cat, packed, w0, data_dir)
    summary["run"]["seconds"] = round(time.time() - t0, 1)
    write_report(Path(a.out), summary)
    print(f"report written to {a.out}/validation.md ({summary['run']['seconds']}s)")
    return 0


def maps_only(mask_dir: Path, out: Path, common: bool = False) -> int:
    """Redo only the per-event daily-map comparison from saved masks (when more maps have arrived)."""
    data_dir = paths.REF / "bashiri" / "data"
    w0, _ = domain_window()
    cat = parse_catalogue(data_dir / "BALMHW_data_info.csv")
    packed = {m: np.load(mask_dir / f"cells_{m}.npy", mmap_mode="r") for m in ("a", "b")
              if (mask_dir / f"cells_{m}.npy").exists()}
    domain = None
    if common:
        with netCDF4.Dataset(data_dir / rdata.SUPP_NAME) as d:
            domain = np.isfinite(np.ma.filled(d["m90"][0], np.nan))
    rows = map_agreement(cat, packed, w0, data_dir, domain)
    out.mkdir(parents=True, exist_ok=True)
    tag = "_common" if common else ""
    (out / f"maps{tag}.json").write_text(json.dumps(rows, indent=1))
    L = ["# Daily-map agreement per event (issue #4)", "", f"masks from {mask_dir}",
         ("Both maps restricted to the authors' effective domain: cells where the published m90 is finite "
          f"({int(domain.sum())} cells)." if common else "Whole sea mask (BALarea)."), ""]
    for m in packed:
        ok = [r for r in rows if m in r]
        j = np.array([r[m]["jaccard"] for r in ok]) if ok else np.array([np.nan])
        L += [f"## Mode ({m})", "", f"- events with a readable map: {len(ok)} of {len(rows)}; "
              f"missing {sum(1 for r in rows if r.get('missing'))}, unreadable {sum(1 for r in rows if 'unreadable' in r)}",
              f"- jaccard min {np.nanmin(j):.6f}, mean {np.nanmean(j):.6f}, perfect {int((j == 1).sum())}", "",
              "| event | days | dates ok | both | only published | only ours | jaccard | exact days |", "|---|---|---|---|---|---|---|---|"]
        for r in ok:
            v = r[m]
            L.append(f"| {r['file'][13:16]} | {r['n_days']} | {r['days_ok']} | {v['both']} | {v['only_published']} | "
                     f"{v['only_ours']} | {v['jaccard']:.4f} | {v['days_exact']} |")
        L.append("")
    (out / f"maps{tag}.md").write_text("\n".join(L))
    print(f"maps written to {out}/maps{tag}.md")
    return 0


def events_by_domain(mask_dir: Path, out: Path, chunk: int = 256) -> int:
    """The domain event rule ("a day is active if any cell of the domain is in a per-cell event with a
    finite anomaly") applied to the saved per-cell masks over two domains: BALarea (the sea mask of the
    Step B run) and the authors' effective domain (cells where the published m90 is finite). Per-cell
    detection does not depend on the domain, so this equals running detection on each domain. Check:
    on BALarea the recomputed active days must equal the saved ones."""
    data_dir = paths.REF / "bashiri" / "data"
    w0, w1 = domain_window()
    det_days = np.arange(w0, w1 + 1)
    cat = parse_catalogue(data_dir / "BALMHW_data_info.csv")
    full = CellBox(0, grid.NLAT, 0, grid.NLON)
    with netCDF4.Dataset(data_dir / rdata.SUPP_NAME) as d:
        authors = np.isfinite(np.ma.filled(d["m90"][0], np.nan))
    domains = {"BALarea": sea_mask(full), "authors_domain": authors & sea_mask(full)}
    summary = {"mask_dir": str(mask_dir), "domain_cells": {k: int(v.sum()) for k, v in domains.items()}, "modes": {}}
    for m in ("a", "b"):
        f = mask_dir / f"cells_{m}.npy"
        if not f.exists():
            continue
        packed = np.load(f, mmap_mode="r")
        act = {k: np.zeros(det_days.size, bool) for k in domains}
        for c0 in range(0, det_days.size, chunk):
            bits = np.unpackbits(np.asarray(packed[c0:c0 + chunk]), axis=2, count=grid.NLON).astype(bool)
            for k, dom in domains.items():
                act[k][c0:c0 + chunk] = (bits & dom).any(axis=(1, 2))
        saved = np.load(mask_dir / f"active_{m}.npy")
        summary["modes"][m] = {"recomputed_BALarea_equals_saved": bool(np.array_equal(act["BALarea"], saved))}
        for k in domains:
            summary["modes"][m][k] = compare_events(cat, core_events(det_days, act[k]))
            summary["modes"][m][k]["active_days"] = int(act[k].sum())
    out.mkdir(parents=True, exist_ok=True)
    (out / "events_by_domain.json").write_text(json.dumps(summary, indent=1, default=str))
    L = ["# Step B events on two domains (issue #4)", "",
         f"Per-cell masks from {mask_dir} (Step B run, commit 411ee03). The domain event rule is re-applied on:",
         f"- BALarea, the bathymetry mask of the Step B run: {summary['domain_cells']['BALarea']} cells;",
         f"- the authors' effective domain, where the published m90 is finite: {summary['domain_cells']['authors_domain']} cells.", "",
         "Two causes separate:",
         "- (b) on the authors' domain vs (b) on BALarea gives the domain effect;",
         "- (a) vs (b) on the authors' domain holds the SST fixed (ours) and changes only the thresholds: the **threshold effect**.",
         "- The **SST effect** is (a) against the published events: the published thresholds are fixed and the SST changes.", "",
         "| mode | domain | events | exact onset+end (of 189) | published overlapped | by several | ours overlapping none | active days | onset offset bins | end offset bins |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for m, v in summary["modes"].items():
        for k in domains:
            e = v[k]
            L.append(f"| {m} | {k} | {e['ours']} | {e['exact_matches']} | {e['published_overlapped']} | "
                     f"{e['published_overlapped_by_several']} | {e['ours_overlapping_none']} | {e['active_days']} | "
                     f"{e['onset_offset_hist_clip10']} | {e['end_offset_hist_clip10']} |")
    L += ["", "Check: active days recomputed on BALarea equal the Step B run's own: "
          + ", ".join(f"mode {m} {v['recomputed_BALarea_equals_saved']}" for m, v in summary["modes"].items()), "",
          "Offsets are ours minus published, in days, clipped to plus or minus 10, for each published event against the overlapping one of ours with the largest overlap."]
    (out / "events_by_domain.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


def core_events(days: np.ndarray, active: np.ndarray):
    from . import _events_from_active
    return _events_from_active(days, active)


if __name__ == "__main__":
    raise SystemExit(main())
