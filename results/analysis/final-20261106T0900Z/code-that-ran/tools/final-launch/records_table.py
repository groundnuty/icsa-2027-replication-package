"""The sealed records table (lane-snap6, 6 Nov; the operator via science #34 05:56Z): per option x layout x record, how well each record flags the runs that omit, with the self-report beside. A COMPOSITION: nothing in icsa/ is changed.
   python records_table.py <seal dir> --part primary|own|all --out-dir DIR [--tree <the pinned measure tree>]
 PART primary (after the H3 measure): from h3/measure/record.csv (the registered reading = reading `primary`, variant `base`, the run level; pooled over models within a layout = model '*'), the confusion counts (tp = flagged and omitting,
   fp = flagged and not omitting, fn = missed, tn), recall and precision with the measure's own intervals AND Wilson 95% on the pooled counts; the self-report (h3/measure/self_report.json: tp/fp/fn/tn, recall, precision) with Wilson 95% added;
   T-unpaginated S1 computed with the SAME frozen functions (measure.record_measure / self_report with H3_OPTIONS set to ('T-unpaginated',) in THIS process only), every such row marked
   "outside H3's registered options (H3_OPTIONS = D, M, T), descriptive"; and the freshness block (each store's last completed extract pass vs t, and for every stale store the counts of its runs per option x layout).
 PART own (after the layout stage): the same rows from layout/h3-own/measure/record.csv (the reading that treats runs that read the OTHER layout's file as not testable) for every cell, side by side with the registered one for T and D in S1,
   with the runs per cell by layout_read (own / other / none) from layout/layout_read.csv.
 Written to DIR (mode 600): records_table.csv (long: one row per cell x record x reading_set x source), records_freshness.csv, records_table.json (account). Counts and rates of detection only; no run key."""
import csv, json, math, os, sys
from pathlib import Path
import pandas as pd

arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
seal = Path(sys.argv[1]); part = arg("--part", "all"); outd = Path(arg("--out-dir", str(seal / "records-table")))
outd.mkdir(parents=True, exist_ok=True)
DESC = "outside H3's registered options (H3_OPTIONS = D, M, T), descriptive"
Z = 1.959964


def wilson(k, n):
    if not n:
        return (float("nan"), float("nan"))
    p = k / n; d = 1 + Z * Z / n; c = p + Z * Z / (2 * n); h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def rate(d):
    """(point, lo, hi, kind) of a measure rate dict: pooled = {point, interval, kind}, per cell = {value, wilson95}."""
    if not isinstance(d, dict):
        return (d, None, None, None)
    iv = d.get("interval") or d.get("wilson95")
    pt = d.get("point", d.get("value"))
    return (pt, iv[0] if iv else None, iv[1] if iv else None, d.get("kind") or ("wilson95" if d.get("wilson95") else None))


def conf_rows(tp, fp, fn, tn):
    """recall = tp/(tp+fn), precision = tp/(tp+fp), each with Wilson 95% from the counts."""
    rl, rh = wilson(tp, tp + fn); pl, ph = wilson(tp, tp + fp)
    return {"tp_flagged_and_omitting": tp, "fp_flagged_not_omitting": fp, "fn_missed": fn, "tn": tn,
            "recall_from_counts": tp / (tp + fn) if (tp + fn) else float("nan"), "recall_wilson_lo": rl, "recall_wilson_hi": rh,
            "precision_from_counts": tp / (tp + fp) if (tp + fp) else float("nan"), "precision_wilson_lo": pl, "precision_wilson_hi": ph}


def from_record_csv(path, reading_set, source, blocks=("main", "pagination")):
    """Pooled-over-models rows (model '*') of the registered reading (primary, base) from a measure record.csv: one row per block x record x option x layout."""
    t0 = pd.read_csv(path)
    t = t0[(t0["model"].astype(str) == "*") & (t0["reading"] == "primary") & (t0["variant"] == "base") & (t0["block"].isin(blocks))]
    out = []
    nt = t0[(t0["model"].astype(str) == "*") & (t0["status"] != "ok") & (t0["block"].isin(blocks))]      # cells that are not testable by design (the audit in S2): listed, with their counts if the measure kept them
    for (blk, rec, opt, lay), g in nt.groupby(["block", "record", "option", "layout"], sort=True):
        r = g.iloc[0]
        out.append({"reading_set": reading_set, "source": source, "block": blk, "record": rec, "option": opt, "layout": lay, "status": r["status"], "marking": "not testable by design (one file, opened either way: no rate)",
                    "n_scored": r.get("n_scored"), "n_runs": r.get("n_runs")})
    for (blk, rec, opt, lay), g in t.groupby(["block", "record", "option", "layout"], sort=True):
        r = g[g["metric"] == "recall"].iloc[0]; p = g[g["metric"] == "precision"].iloc[0]
        base = {"reading_set": reading_set, "source": source, "block": blk, "record": rec, "option": opt, "layout": lay, "status": r["status"], "marking": "",
                "n_scored": r.get("n_scored"), "n_runs": r.get("n_runs"), "n_models": r.get("n_models"),
                "recall_measure": r["value"], "recall_measure_lo": r["ci_lo"], "recall_measure_hi": r["ci_hi"], "recall_ci_kind": r["ci_kind"],
                "precision_measure": p["value"], "precision_measure_lo": p["ci_lo"], "precision_measure_hi": p["ci_hi"], "precision_ci_kind": p["ci_kind"]}
        if r["status"] == "ok" and pd.notna(r.get("tp")):
            base |= conf_rows(int(r["tp"]), int(r["fp"]), int(r["fn"]), int(r["tn"]))
        out.append(base)
    return out


def self_rows(path, reading_set, source, extra_marking=""):
    d = json.load(open(path))
    out = []
    for blk, cells in d["blocks"].items():
        if blk not in ("main", "pagination"):
            continue
        for key, v in cells.items():
            opt, lay, model = key.split("|")
            if model != "*":
                continue
            row = {"reading_set": reading_set, "source": source, "block": blk, "record": "self_report", "option": opt, "layout": lay, "status": "ok", "marking": extra_marking,
                   "excluded_runs": json.dumps(v.get("excluded")) if isinstance(v.get("excluded"), (dict, list)) else v.get("excluded")}
            if all(k in v for k in ("tp", "fp", "fn", "tn")):
                row |= conf_rows(int(v["tp"]), int(v["fp"]), int(v["fn"]), int(v["tn"]))
            (row["recall_measure"], row["recall_measure_lo"], row["recall_measure_hi"], row["recall_ci_kind"]) = rate(v.get("recall"))
            (row["precision_measure"], row["precision_measure_lo"], row["precision_measure_hi"], row["precision_ci_kind"]) = rate(v.get("precision"))
            out.append(row)
    return out


rows = []
account = {"part": part}
if part in ("primary", "all"):
    rows += from_record_csv(seal / "h3" / "measure" / "record.csv", "registered", "h3/measure/record.csv")
    rows += self_rows(seal / "h3" / "measure" / "self_report.json", "registered", "h3/measure/self_report.json")
    # T-unpaginated S1: the same frozen functions, H3_OPTIONS set for this process only (the measure module is not changed on disk)
    try:
        tree = arg("--tree")
        if tree:
            sys.path.insert(0, tree)
        from icsa.faults.mainaudit import measure as M
        M.H3_OPTIONS = ("T-unpaginated",)
        rws = M.load(str(seal / "h3" / "scored_rows_coded.jsonl"), str(seal / "h3" / "platform_rows.jsonl"))
        blocks = M.by_block(rws)
        boot = M.registered_bootstrap()
        day = None
        dt_dir = seal / "frozen" / "daytruth"
        if dt_dir.is_dir():
            try:
                import hashlib
                day = M.load_day_truth(str(dt_dir), M.labeller_hash(Path(tree) if tree else Path(os.getcwd())))
            except Exception:       # noqa: BLE001
                day = None
        tu = {"blocks": {b: M.record_measure(g, day, boot=boot) for b, g in blocks.items()}}
        n_tu = 0
        for b, cells in tu["blocks"].items():
            for key, c in cells.items():
                rec, opt, lay, model = key.split("|")
                if model != "*" or c.get("status") != "ok":
                    if model == "*" and c.get("status") != "ok":
                        rows.append({"reading_set": "registered", "source": "computed here (frozen functions)", "block": b, "record": rec, "option": opt, "layout": lay, "status": c.get("status"), "marking": DESC})
                    continue
                pr = c["readings"]["primary"]["base"]
                row = {"reading_set": "registered", "source": "computed here (frozen measure.record_measure with H3_OPTIONS=('T-unpaginated',))", "block": b, "record": rec, "option": opt, "layout": lay,
                       "status": "ok", "marking": DESC, "n_scored": c.get("n_scored"), "n_models": len(c.get("models", []))}
                cs = pr.get("counts_sum") or {}
                if all(k in cs for k in ("tp", "fp", "fn", "tn")):
                    row |= conf_rows(int(cs["tp"]), int(cs["fp"]), int(cs["fn"]), int(cs["tn"]))
                (row["recall_measure"], row["recall_measure_lo"], row["recall_measure_hi"], row["recall_ci_kind"]) = rate(pr.get("recall"))
                (row["precision_measure"], row["precision_measure_lo"], row["precision_measure_hi"], row["precision_ci_kind"]) = rate(pr.get("precision"))
                row["n_runs"] = pr.get("n_runs")
                rows.append(row); n_tu += 1
        sr = M.self_report(M.by_block(rws).get("pagination", []), boot) if "pagination" in M.by_block(rws) else {}
        for key, v in sr.items():
            opt, lay, model = key.split("|")
            if model == "*" and all(k in v for k in ("tp", "fp", "fn", "tn")):
                row = {"reading_set": "registered", "source": "computed here (frozen measure.self_report)", "block": "pagination", "record": "self_report", "option": opt, "layout": lay, "status": "ok", "marking": DESC,
                       **conf_rows(int(v["tp"]), int(v["fp"]), int(v["fn"]), int(v["tn"]))}
                (row["recall_measure"], row["recall_measure_lo"], row["recall_measure_hi"], row["recall_ci_kind"]) = rate(v.get("recall"))
                (row["precision_measure"], row["precision_measure_lo"], row["precision_measure_hi"], row["precision_ci_kind"]) = rate(v.get("precision"))
                rows.append(row)
        account["t_unpaginated_rows"] = n_tu
    except Exception as e:      # noqa: BLE001 -- soft: the registered part still stands
        account["t_unpaginated_error"] = f"{type(e).__name__}: {str(e)[:160]}"
if part in ("own", "all"):
    own_p = seal / "layout" / "h3-own" / "measure" / "record.csv"
    if own_p.is_file():
        rows += from_record_csv(own_p, "own_layout_only", "layout/h3-own/measure/record.csv")
        sp = seal / "layout" / "h3-own" / "measure" / "self_report.json"
        if sp.is_file():
            rows += self_rows(sp, "own_layout_only", "layout/h3-own/measure/self_report.json")
        lr = seal / "layout" / "layout_read.csv"
        if lr.is_file():
            t = pd.read_csv(lr, usecols=["option", "layout", "layout_read", "block"])
            t = t[t["block"].isin(["main", "pagination"])]
            cnt = t.groupby(["option", "layout", "layout_read"]).size().rename("runs").reset_index()
            cnt.to_csv(outd / "records_layout_read_counts.csv", index=False)
            account["layout_read_counts_rows"] = len(cnt)
    else:
        account["own_part"] = "layout/h3-own/measure/record.csv does not exist in this seal (the layout stage has not produced it)"

# the freshness block: the H3 stage's own line (each store's last completed pass vs t) and the runs of every stale store per option x layout
fresh = []
try:
    line = next((l for l in (seal / "h3" / "measure.out").read_text().splitlines() if False), None)
except OSError:
    line = None
try:
    txt = ""
    for p in (seal / "logs" / "h3.out", seal / "h3" / "extract_check.out"):
        if p.is_file():
            txt += p.read_text() + "\n"
    import re
    m = re.search(r"last completed extract pass vs t \(s\):(.*)", txt)
    ages = {}
    if m:
        for tok in m.group(1).split():
            mm = re.match(r"(\S+?)=(-?\d+)(\(STALE\))?$", tok)
            if mm:
                ages[mm.group(1)] = (int(mm.group(2)), bool(mm.group(3)))
    prov = json.load(open(seal / "M" / "providers.json"))["providers"]
    import sqlite3
    c = sqlite3.connect(f"file:{seal}/out/work/cut/state.sqlite?mode=ro", uri=True)
    runs = {k: (o, l) for k, o, l in c.execute("select run_key, option, layout from runs")}
    c.close()
    own = {}
    for k, (o, l) in runs.items():
        own.setdefault(prov.get(k, "?"), {}).setdefault((o, l), 0)
        own[prov.get(k, "?")][(o, l)] += 1
    for store, (age, stale) in sorted(ages.items()):
        base = {"store": store, "last_completed_pass_vs_t_s": age, "stale": stale}
        if stale:
            for (o, l), n in sorted(own.get("site_g" if store == "site_g" else store, {}).items()):
                fresh.append(base | {"option": o, "layout": l, "runs_owned_by_this_stale_store": n})
        else:
            fresh.append(base | {"option": "", "layout": "", "runs_owned_by_this_stale_store": ""})
    account["stores_in_freshness_block"] = len(ages); account["stale_stores"] = sum(1 for a in ages.values() if a[1])
except Exception as e:      # noqa: BLE001
    account["freshness_error"] = f"{type(e).__name__}: {str(e)[:160]}"

if rows:
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    p = outd / f"records_table_{part}.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    os.chmod(p, 0o600)
if fresh:
    p = outd / "records_freshness.csv"
    pd.DataFrame(fresh).to_csv(p, index=False); os.chmod(p, 0o600)
account["rows"] = len(rows)
p = outd / f"records_table_{part}.json"
p.write_text(json.dumps(account, indent=1, sort_keys=True)); os.chmod(p, 0o600)
print("records table: " + json.dumps(account, sort_keys=True))
