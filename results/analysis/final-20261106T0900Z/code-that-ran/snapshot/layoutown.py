"""The own-layout tables and the within-environment tables beside every contrast (#34, science's rulings of 5 Nov): the frozen analysis run again on a subset of the UNITS,
into side directories of the seal, and a table per contrast table that sets the analyses side by side.

    python -m snapshot.layoutread own <seal> [--variants own-only,env-vm,env-hpc] [--field layout_read|layout_read_with_perf] [--h3-table F] [--config F] [--overhead F|none] ...

A UNIT is instance x layout x model (within a block): every option and seed of it. The subsets are of units, never of runs, so the model mix and the pairing across options
do not change (science, #34 01:37Z):
- `own-only`: a unit leaves, for levels and contrasts alike, when ANY of its runs, T-unpaginated included, read the sibling layout's directory (`other`, `both`, or partial
  evidence that already shows a sibling read). A unit with no evidence stays and is counted.
- `own-only-strict` (off unless asked): a unit also leaves when any of its runs has no `layout_read` value.
- `env-vm`, `env-hpc` (science, #34 01:41Z): a unit counts only when ALL its runs actually ran in one environment, the VM or HPC (from the winning attempt's store: the run's owner
  provider, `environment` in layout_read.csv), whatever group it was dealt to; each environment is one analysis, and the contrasts of the two are set side by side.

Reads `<seal>/layout/layout_read.csv` (made by `layoutread read`) and the seal's own analysis inputs (`out-coded/` if it exists, else `out/`: the scored rows, `infra.json`,
`causes.csv`, `cause_flags.csv`, the coders' labels and coverage), drops the units, and calls the SAME frozen `icsa.analysis.run.run_all` that `snapshot analyse` calls, with
the same overhead, fidelity rows and inspection input (from the seal's `SNAPSHOT.json`; `--h3-table` is not recorded there, so the driver passes the one it passed to the
snapshot). The infra account (analysed, exhausted and unfinished runs) and the coders' labels follow the units. Nothing in `icsa/` or in the pinned H3 measure is changed. The
primary tables stay as they are; everything here is written to the sealed path only.

Each variant holds `tables/` (the full analysis, every table stamped with the snapshot's own first line), `inputs/` (the filtered inputs it took), `units.csv` (every unit, its
environment, kept or left and why), `units_by_model.csv`, `dropped_runs.csv`; `layout/<own-only>/beside/<table>.csv` and `layout/environments/beside/<table>.csv` set the primary
and the variant(s) side by side for every table with an effect per `layout` and `contrast`. `layout/environment_units.json` says how many units qualify. All sealed: nothing here
is printed or quoted."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse         # noqa: E402
import csv              # noqa: E402
import json             # noqa: E402
from collections import Counter     # noqa: E402
from pathlib import Path    # noqa: E402

from . import layoutread as L   # noqa: E402

VARIANTS = ("own-only", "own-only-strict", "env-vm", "env-hpc", "bytes-measured")
DEFAULT_VARIANTS = "own-only,env-vm,env-hpc,bytes-measured"
COMPARED = ("T", "D", "M")            # the options of the pre-registered contrasts (`[inference] main_options`); the run overrides it from the analysis config
IDENT = ("block", "scenario", "extent", "T_seeds", "sensitivity", "definitions_used", "variant", "imputed_as", "rates_source", "outcome", "layout", "contrast",
         "option_a", "option_b")
VALUES = ("effect", "ci_lo", "ci_hi", "p_holm", "significant", "at_least_smallest", "n_regions", "n_models", "n_regions_dropped")


# ---- units -----------------------------------------------------------------------------------------------------------------------------
PRIMARY_BLOCKS = ("main", "pagination")      # the analysis's own `[blocks] primary` (icsa/analysis/preregistered.toml): T-unpaginated is in `pagination`, T, D and M in `main`


def unit_of(block: str, instance: str, layout: str, model: str, primary: tuple[str, ...] = PRIMARY_BLOCKS) -> tuple[str, str, str, str]:
    """The unit of a run: instance x layout x model. The primary blocks are ONE group, so T-unpaginated (block `pagination`) is in the unit of the T, D and M runs of
    `main`; any other block (the pilot, which feeds only the power re-estimate) is its own, never joined to main's."""
    return ("primary" if block in primary else block, instance, layout, model)


def unit_environments(rows: list[dict], exhausted: list[dict], owner: dict[str, str], envmap: dict[str, str], primary: tuple[str, ...] = PRIMARY_BLOCKS) -> dict[tuple, str]:
    """{unit: vm | hpc | mixed | unknown}: where every run of the unit that ran, ran. A run that ran is a scored run (its `environment` is in layout_read.csv) or an exhausted one (its
    owner provider from the merge's providers.json). A run that never started has no environment and is not asked: its owner in the merge would only be main by default."""
    envs: dict[tuple, set[str]] = {}
    for r in rows:
        envs.setdefault(unit_of(r["block"], r["instance"], r["layout"], r["model"], primary), set()).add(r["environment"] or "unknown")
    for e in exhausted:
        prov = owner.get(e["run_key"])
        envs.setdefault(unit_of(e["block"], e["instance_id"], e["layout"], e["model"], primary), set()).add(L.environment_of(prov, envmap) or "unknown")
    return {u: ("unknown" if "unknown" in s else next(iter(s)) if len(s) == 1 else "mixed") for u, s in envs.items()}


def plan(rows: list[dict], variant: str, envs: dict[tuple, str], field: str = "layout_read", primary: tuple[str, ...] = PRIMARY_BLOCKS,
         compared: tuple[str, ...] = COMPARED) -> dict:
    """Which units this variant leaves out. Returns {units: [{unit, runs, environment, status, reason, runs_unknown}], drop_units, drop_runs {(block, run): reason}}."""
    by_unit: dict[tuple, list[dict]] = {}
    for r in rows:
        by_unit.setdefault(unit_of(r["block"], r["instance"], r["layout"], r["model"], primary), []).append(r)
    for u in envs:
        by_unit.setdefault(u, [])                     # a unit of exhausted runs only
    out, drop_units, drop_runs = [], set(), {}
    for u in sorted(by_unit):
        rs = by_unit[u]
        sibling = [(r, L.drop_reason(r, field)) for r in rs]
        sibling = [(r, w) for r, w in sibling if w]
        unknown = [r for r in rs if not r[field]]
        by_opt = {o: [r for r in rs if r["option"] == o] for o in compared}
        # H2's bytes: a unit counts only when every compared option was MEASURED: it has runs of the option and each has its bytes between the sites (strict); `lenient`: at least one run
        # of each does (what the frozen contrast would use, as it takes the mean of the measured seeds). An unknown is never a 0.
        bytes_strict = all(by_opt[o] and all(r["bytes_between_sites"] != "" for r in by_opt[o]) for o in compared)
        bytes_lenient = all(by_opt[o] and any(r["bytes_between_sites"] != "" for r in by_opt[o]) for o in compared)
        why = None
        if variant in ("own-only", "own-only-strict") and sibling:
            why = "unit_sibling_read"
        elif variant == "own-only-strict" and unknown:
            why = "unit_no_layout_read_value"
        elif variant in ("env-vm", "env-hpc") and envs.get(u, "unknown") != variant[4:]:
            why = f"unit_environment_{envs.get(u, 'unknown')}"
        elif variant == "bytes-measured" and not bytes_strict:
            why = "unit_bytes_between_sites_not_measured"
        if why:
            drop_units.add(u)
            for r in rs:
                own = L.drop_reason(r, field)
                drop_runs[(r["block"], r["run"])] = f"{why}:{own}" if own else why
        out.append({"unit": u, "n_runs": len(rs), "environment": envs.get(u, "unknown"), "status": "left" if why else "kept", "reason": why or "",
                    "runs_without_value": len(unknown), "bytes_measured": bytes_strict, "bytes_measured_lenient": bytes_lenient})
    return {"units": out, "drop_units": drop_units, "drop_runs": drop_runs, "primary": primary}


def bytes_units_summary(units: list[dict], compared: tuple[str, ...]) -> dict:
    """How many units have every compared option measured for the bytes between the sites: all units, and those of the primary blocks (the ones H2's contrast rests on; the pilot is its own group)."""
    prim = [u for u in units if u["unit"][0] == "primary"]
    return {"units": len(units), "qualifying": sum(u["bytes_measured"] for u in units), "qualifying_lenient": sum(u["bytes_measured_lenient"] for u in units),
            "primary_units": len(prim), "primary_qualifying": sum(u["bytes_measured"] for u in prim), "primary_qualifying_lenient": sum(u["bytes_measured_lenient"] for u in prim),
            "compared_options": list(compared)}


def units_by_model(units: list[dict], variant: str) -> list[dict]:
    """Per model: how many units there are, how many leave, how many stay (and of those, how many hold a run with no value)."""
    out = []
    for model in sorted({u["unit"][3] for u in units}):
        us = [u for u in units if u["unit"][3] == model]
        row = {"model": model, "units": len(us), "units_left": sum(u["status"] == "left" for u in us), "units_kept": sum(u["status"] == "kept" for u in us),
               "units_kept_with_a_run_without_value": sum(u["status"] == "kept" and u["runs_without_value"] > 0 for u in us),
               "units_bytes_measured": sum(u["bytes_measured"] for u in us), "units_bytes_measured_lenient": sum(u["bytes_measured_lenient"] for u in us)}
        env = Counter(u["environment"] for u in us)
        row.update({f"units_{e}": env.get(e, 0) for e in ("vm", "hpc", "mixed", "unknown")})
        out.append(row)
    return out


# ---- filters ---------------------------------------------------------------------------------------------------------------------------
def filter_jsonl(src: Path, dst: Path, drop: set[tuple[str, str]]) -> tuple[int, int]:
    """Copies the records of `src` (JSONL keyed by `block` and `run_key`) that are not dropped; returns (kept, dropped)."""
    kept = gone = 0
    out = []
    with open(src) as fh:
        for line in fh:
            if not line.strip():
                continue
            d = json.loads(line)
            if (d.get("block"), d.get("run_key")) in drop:
                gone += 1
            else:
                kept += 1
                out.append(line.rstrip("\n"))
    L.write_atomic(dst, "".join(x + "\n" for x in out))
    return kept, gone


def filter_infra(src: Path, dst: Path, drop: set[tuple[str, str]], drop_units: set[tuple] | None = None, primary: tuple[str, ...] = PRIMARY_BLOCKS) -> int:
    """infra.json without the dropped runs' `analysed_attempts` (the analysis refuses a done run with no scored row), and without the exhausted and unfinished runs of a dropped
    unit: the unit leaves with all of its runs. The discarded usage is per cell, not per run, and stays. Returns the analysed attempts dropped."""
    d = json.loads(Path(src).read_text())
    before = len(d["analysed_attempts"])
    d["analysed_attempts"] = [a for a in d["analysed_attempts"] if (a["block"], a["key"]) not in drop]
    if drop_units:
        for k in ("exhausted_runs", "unfinished_runs"):
            d[k] = [e for e in d.get(k, []) if unit_of(e["block"], e["instance_id"], e["layout"], e["model"], primary) not in drop_units]
    L.write_atomic(dst, json.dumps(d, indent=1))
    return before - len(d["analysed_attempts"])


# ---- the pairs -------------------------------------------------------------------------------------------------------------------------
def _read_pair(p: Path, q: Path):
    import pandas as pd
    try:
        a, b = pd.read_csv(p, skiprows=1), pd.read_csv(q, skiprows=1)
    except pd.errors.EmptyDataError:        # a table with no column at all (the stamp line and a blank line): it holds no contrast
        return None
    if not {"layout", "contrast", "effect"} <= set(a.columns) or not {"layout", "contrast", "effect"} <= set(b.columns):
        return None
    return a, b


def beside(primary_dir: Path, own_dir: Path, out_dir: Path, line: str) -> list[str]:
    """For each table both analyses wrote that has `layout`, `contrast` and `effect`: the rows of the two side by side, keyed by the identifying columns."""
    import pandas as pd
    written = []
    for p in sorted(Path(primary_dir).glob("*.csv")):
        q = Path(own_dir) / p.name
        if not q.is_file():
            continue
        pair = _read_pair(p, q)
        if pair is None:
            continue
        a, b = pair
        keys = [c for c in IDENT if c in a.columns and c in b.columns]
        vals = [c for c in VALUES if c in a.columns and c in b.columns]
        m = a[keys + vals].merge(b[keys + vals], on=keys, how="outer", suffixes=("_primary", "_own_only"), indicator=True)
        m = m.rename(columns={"_merge": "present_in"})
        m["present_in"] = m["present_in"].map({"both": "both", "left_only": "primary_only", "right_only": "own_only_only"})
        ep, eo = m["effect_primary"], m["effect_own_only"]
        m["direction_changed"] = ((ep * eo) < 0).where(ep.notna() & eo.notna())               # a sign change; empty where either side has no effect
        if "at_least_smallest_primary" in m:
            ap, ao = m["at_least_smallest_primary"], m["at_least_smallest_own_only"]
            m["threshold_crossed"] = (ap.astype("object") != ao.astype("object")).where(ap.notna() & ao.notna())
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        L.write_atomic(Path(out_dir) / p.name, line + "\n" + m.to_csv(index=False))
        written.append(p.name)
    return written


def beside_environments(primary_dir: Path, env_dirs: dict[str, Path], out_dir: Path, line: str) -> list[str]:
    """Like `beside`, with one column set per environment (`vm`, `hpc`) next to the primary's, in one table per contrast table."""
    import pandas as pd
    written = []
    for p in sorted(Path(primary_dir).glob("*.csv")):
        got = {}
        for name, d in env_dirs.items():
            q = Path(d) / p.name
            pair = _read_pair(p, q) if q.is_file() else None
            if pair is not None:
                got[name] = pair
        if not got:
            continue
        a = next(iter(got.values()))[0]
        keys = [c for c in IDENT if c in a.columns and all(c in b.columns for _, b in got.values())]
        vals = [c for c in VALUES if c in a.columns and all(c in b.columns for _, b in got.values())]
        m = a[keys + vals].rename(columns={c: f"{c}_primary" for c in vals})
        m["in_primary"] = True
        for name, (_, b) in got.items():
            bb = b[keys + vals].rename(columns={c: f"{c}_{name}" for c in vals})
            bb[f"in_{name}"] = True
            m = m.merge(bb, on=keys, how="outer")
        for c in [c for c in m.columns if c.startswith("in_")]:
            m[c] = m[c].astype("object").where(m[c].notna(), False)
        for name in got:
            ep, ee = m["effect_primary"], m[f"effect_{name}"]
            m[f"direction_changed_{name}"] = ((ep * ee) < 0).where(ep.notna() & ee.notna())
            if "at_least_smallest_primary" in m:
                ap, ae = m["at_least_smallest_primary"], m[f"at_least_smallest_{name}"]
                m[f"threshold_crossed_{name}"] = (ap.astype("object") != ae.astype("object")).where(ap.notna() & ae.notna())
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        L.write_atomic(Path(out_dir) / p.name, line + "\n" + m.to_csv(index=False))
        written.append(p.name)
    return written


def h2_beside(primary_dir: Path, variant_dir: Path, out_dir: Path, line: str) -> list[str]:
    """H2's bytes contrast on the units whose compared options were all measured, beside the primary's: the bytes rows of `h4_directions.csv` (the descriptive table that carries the bytes between
    the sites, on the log2 scale: a pooled effect and its ratio) of the two analyses, per layout and contrast. The primary's mean uses the measured seeds of every unit; this one only the units that
    qualify."""
    import pandas as pd
    try:
        a = pd.read_csv(Path(primary_dir) / "h4_directions.csv", skiprows=1)
        b = pd.read_csv(Path(variant_dir) / "h4_directions.csv", skiprows=1)
    except (OSError, pd.errors.EmptyDataError):
        return []
    a, b = a[a["outcome"] == "bytes_between_sites"], b[b["outcome"] == "bytes_between_sites"]
    keys = ["layout", "contrast"]
    vals = [c for c in ("pooled_effect", "pooled_effect_ratio", "pooled_ci_lo", "pooled_ci_hi", "n_models", "n_models_agreeing") if c in a.columns and c in b.columns]
    m = a[keys + vals].merge(b[keys + vals], on=keys, how="outer", suffixes=("_primary", "_measured_units"))
    ep, em = m["pooled_effect_primary"], m["pooled_effect_measured_units"]
    m["direction_changed"] = ((ep * em) < 0).where(ep.notna() & em.notna())
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    L.write_atomic(Path(out_dir) / "h2_bytes.csv", line + "\n" + m.to_csv(index=False))
    return ["h2_bytes.csv"]


# ---- side tables, outside the frozen analysis -------------------------------------------------------------------------------------------------
def cell_day_iou_side(seal: Path, base: Path, snap: dict, cfg, bootstrap: bool = True) -> int:
    """`cell_day_iou` (the registered per-run measure of the agent's cell-day mask against the reference's: `ScoredRow.cell_day_iou`, None where the run has none) as a REGION-LEVEL contrast, by
    the frozen tool and method of the existing contrasts (`contrasts.instance_values`, then `contrast_one`: instance = mean of the seeds that have a value, region = mean over the instances an arm
    has, paired by region, the equal-model mean, the region bootstrap and the Wilcoxon p), for every contrast and layout of the pre-registered list. A SIDE table: it is not in the Holm family (no
    `p_holm`, no verdict on it), the frozen analysis and its tables are unchanged, and the value is not in the analysis's frame (`adapter.COLUMNS` has no `cell_day_iou`), so it is read from the scored
    rows beside it, on the same run population (`rows_to_frame`: the primary blocks, the same cohort). Writes `<seal>/layout/side/cell_day_iou_contrasts.csv` and `..._per_model.csv`, stamped like the
    snapshot's tables; returns the number of contrast rows."""
    import numpy as np
    import pandas as pd
    from icsa.analysis import adapter, contrasts as C
    from . import stamp
    d = L.layout_dir(seal) / "side"
    if (d / "cell_day_iou_contrasts.csv").exists():
        raise L.LayoutReadError(f"{d / 'cell_day_iou_contrasts.csv'} exists: never overwritten (move it aside)")
    rows = adapter.load_jsonl(base / "pipeline" / "scored_rows.jsonl")
    df = adapter.rows_to_frame(rows, cfg)
    val = {(r.block, r.run.key()): r.cell_day_iou for r in rows}
    df["cell_day_iou"] = pd.to_numeric([val.get((b, k)) for b, k in zip(df["block"], df["run_key"])], errors="coerce")      # None is NaN: an unknown is never a 0
    out = C.Outcome("cell_day_iou", "cell_day_iou", False, "proportion", None)
    main = df[df.option.isin(cfg.options)]
    inst = C.instance_values(main, out.column, defined_only=False)
    rng = np.random.default_rng(cfg["bootstrap"]["seed"])
    tab, pms = [], []
    for layout in cfg.layouts:
        for a, b in cfg.contrasts:
            r, pm = C.contrast_one(inst, a, b, layout, out, cfg, bootstrap, rng)
            tab.append(r)
            pms.append(pm)
    t = pd.DataFrame(tab)
    t["p_holm"] = np.nan
    t["holm"] = "outside the Holm family: a side table"
    pm = pd.concat([p for p in pms if len(p)], ignore_index=True) if any(len(p) for p in pms) else pd.DataFrame(columns=["outcome", "layout", "contrast", "model", "effect"])
    d.mkdir(mode=0o700, exist_ok=True)
    tmp = d / "cell-day-iou-tables"
    tmp.mkdir(mode=0o700)
    t.to_csv(tmp / "cell_day_iou_contrasts.csv", index=False)
    pm.to_csv(tmp / "cell_day_iou_per_model.csv", index=False)
    stamp.stamp_tables(tmp, stamp.header(bool(snap["final"]), snap["t"]))
    for p in tmp.iterdir():
        p.replace(d / p.name)
    tmp.rmdir()
    return len(t)


def coverage_finished_side(seal: Path, base: Path, snap: dict, cfg, bootstrap: bool = True) -> int:
    """Coverage on FINISHED runs only (science, #34 16:33Z), beside the frozen all-runs coverage, which stays primary: the scorer attaches an extent to unfinished runs too, so those runs' zeros
    drive the all-runs coverage means. A run is finished as the adapter's omission denominators have it: `finished` and not ended by the time cap. By the frozen tools on the finished-only
    frame, nothing recomputed: the LEVELS (`exhibits.level_table`: region-level mean per option x layout with the region bootstrap) and the CONTRASTS (`contrasts.instance_values` and
    `contrast_one`, every pre-registered pair and layout, no Holm: `p_holm` empty) of `coverage_baseline` and `coverage_target`; and per option x layout x model the runs with NOTHING analysed
    (both coverage points exactly 0), split finished and unfinished, and how many of those have an upper bound above 0 (either coverage's `_upper`; an upper that is not known is counted apart),
    over the frozen analysis's own population (the compared options and T-unpaginated). Written to `<seal>/layout/side/`, stamped. Returns the number of rows written."""
    import numpy as np
    import pandas as pd
    from icsa.analysis import adapter, contrasts as C, exhibits as X, inspection as INS, secondary as S
    from . import stamp
    d = L.layout_dir(seal) / "side"
    if (d / "coverage_finished_contrasts.csv").exists():
        raise L.LayoutReadError(f"{d / 'coverage_finished_contrasts.csv'} exists: never overwritten (move it aside)")
    # The frame is the frozen analysis's own: `run_all` applies the coders' decisions (labels after inspection and, where both coders agree exactly, their coverage) to the scored rows BEFORE it builds
    # the frame. Without them the instrument's `unknown` runs (nearly every finished run) have no coverage point, and the finished-only means read 0 over the few runs the instrument itself decided.
    labels = (snap.get("inputs") or {}).get("inspection_labels", "none")
    cov = seal / "frozen" / "inspection-coverage.jsonl"
    ins = INS.InspectionInput.not_run() if labels == "none" else INS.load(Path(labels), cov if cov.is_file() else None)
    df = adapter.rows_to_frame(INS.apply(adapter.load_jsonl(base / "pipeline" / "scored_rows.jsonl"), ins), cfg)
    fin = df["finished"].astype(bool) & ~df["time_cap"].astype(bool)             # one definition, used for the levels, the contrasts and the counts
    dff = df[fin]
    levels = pd.concat([X.level_table(dff, cfg, o, B=None if bootstrap else 50) for o in S.COVERAGE_OUTCOMES], ignore_index=True)
    main = dff[dff.option.isin(cfg.options)]
    rng = np.random.default_rng(cfg["bootstrap"]["seed"])
    rows, pms = [], []
    for name in S.COVERAGE_OUTCOMES:
        o = C.OUTCOME[name]
        inst = C.instance_values(main, o.column, defined_only=False)
        for layout in cfg.layouts:
            for a, b in cfg.contrasts:
                r, pm = C.contrast_one(inst, a, b, layout, o, cfg, bootstrap, rng)
                rows.append(r)
                pms.append(pm)
    con = pd.DataFrame(rows)
    con["p_holm"] = np.nan
    con["holm"] = "outside the Holm family: a side table"
    con["population"] = "finished runs only"
    pm = pd.concat([p for p in pms if len(p)], ignore_index=True) if any(len(p) for p in pms) else pd.DataFrame(columns=["outcome", "layout", "contrast", "model", "effect"])
    pop = df[df.option.isin(cfg.options + [cfg["pagination"]["option"]])]
    pf = fin.loc[pop.index]
    zero = (pop["coverage_baseline"] == 0) & (pop["coverage_target"] == 0)
    ub, ut = pop["coverage_baseline_upper"], pop["coverage_target_upper"]
    up_gt0 = (ub > 0) | (ut > 0)
    up_unknown = ~up_gt0 & (ub.isna() | ut.isna())
    cnt = []
    for (opt, layout, model), g in pop.assign(_fin=pf, _zero=zero, _up=up_gt0, _unk=up_unknown).groupby(["option", "layout", "model"], sort=True):
        zf, zu = g[g["_zero"] & g["_fin"]], g[g["_zero"] & ~g["_fin"]]
        cnt.append({"option": opt, "layout": layout, "model": model, "runs": len(g), "finished": int(g["_fin"].sum()), "unfinished": int((~g["_fin"]).sum()),
                    "zero_both_finished": len(zf), "zero_both_unfinished": len(zu),
                    "zero_both_finished_upper_gt0": int(zf["_up"].sum()), "zero_both_unfinished_upper_gt0": int(zu["_up"].sum()),
                    "zero_both_finished_upper_unknown": int(zf["_unk"].sum()), "zero_both_unfinished_upper_unknown": int(zu["_unk"].sum())})
    counts = pd.DataFrame(cnt, columns=["option", "layout", "model", "runs", "finished", "unfinished", "zero_both_finished", "zero_both_unfinished", "zero_both_finished_upper_gt0",
                                        "zero_both_unfinished_upper_gt0", "zero_both_finished_upper_unknown", "zero_both_unfinished_upper_unknown"])
    d.mkdir(mode=0o700, exist_ok=True)
    tmp = d / "coverage-finished-tables"
    tmp.mkdir(mode=0o700)
    levels.to_csv(tmp / "coverage_finished_levels.csv", index=False)
    con.to_csv(tmp / "coverage_finished_contrasts.csv", index=False)
    pm.to_csv(tmp / "coverage_finished_per_model.csv", index=False)
    counts.to_csv(tmp / "coverage_zero_analysed.csv", index=False)
    stamp.stamp_tables(tmp, stamp.header(bool(snap["final"]), snap["t"]))
    for p in tmp.iterdir():
        p.replace(d / p.name)
    tmp.rmdir()
    return len(levels) + len(con) + len(counts)


def coverage_finished_soft(seal: Path, base: Path, snap: dict, cfg, bootstrap: bool = True) -> dict:
    """`coverage_finished_side` that cannot fail the interim: an exception leaves a note naming only its class (`side/coverage_finished.FAILED.txt`), the traceback goes to stderr, and the
    answer says it failed."""
    try:
        return {"rows": coverage_finished_side(seal, base, snap, cfg, bootstrap)}
    except Exception as e:      # noqa: BLE001
        import traceback
        traceback.print_exc(file=sys.stderr)
        try:
            d = L.layout_dir(seal) / "side"
            d.mkdir(mode=0o700, exist_ok=True)
            (d / "coverage_finished.FAILED.txt").write_text(f"the coverage-on-finished-runs side table was not made: {type(e).__name__}\n")
        except OSError:
            pass
        return {"failed": type(e).__name__}


# ---- the analyses ----------------------------------------------------------------------------------------------------------------------
def own_only(seal: Path, argv: list[str] | None = None, *, cfg=None, bootstrap: bool = True, compared: tuple[str, ...] | None = None) -> dict:
    """Runs each variant. `cfg`/`bootstrap`: a test's small configuration; the driver leaves them as `snapshot analyse` has them."""
    ap = argparse.ArgumentParser(prog="python -m snapshot.layoutread own")
    ap.add_argument("--variants", default=DEFAULT_VARIANTS, help=f"comma list of {VARIANTS}")
    ap.add_argument("--field", choices=["layout_read", "layout_read_with_perf"], default="layout_read")
    ap.add_argument("--parallel", type=int, default=0, help="variants analysed at once, each in its own process (0: all of them, at most 4; 1: one after the other)")
    ap.add_argument("--config")
    ap.add_argument("--h3-table")
    ap.add_argument("--overhead")
    ap.add_argument("--fidelity-rows")
    ns = ap.parse_args(argv or [])
    variants = [v for v in ns.variants.split(",") if v]
    if not variants or any(v not in VARIANTS for v in variants):
        raise L.LayoutReadError(f"--variants: any of {VARIANTS}")
    seal = Path(seal)
    rows = L.load_rows(seal)
    base = L.base_dir(seal)
    snap = json.loads((base / "SNAPSHOT.json").read_text())
    meta = json.loads((seal / "layout" / "layout_read.meta.json").read_text())
    envmap = dict(meta.get("provider_environments") or {})
    owner = json.loads((seal / "M" / "providers.json").read_text())["providers"]
    exhausted = json.loads((base / "pipeline" / "infra.json").read_text()).get("exhausted_runs", [])
    from icsa.analysis import config as cfgmod
    cfg = cfg or cfgmod.load(ns.config)
    primary = tuple(cfg["blocks"]["primary"])
    compared = tuple(compared or cfg.options)
    envs = unit_environments(rows, exhausted, owner, envmap, primary)
    ec = Counter(envs.values())
    eu = L.layout_dir(seal) / "environment_units.json"
    if not eu.exists():                           # how many units qualify for a within-environment table in this snapshot
        L.write_atomic(eu, json.dumps({"units": len(envs), "qualifying": ec.get("vm", 0) + ec.get("hpc", 0), "vm": ec.get("vm", 0), "hpc": ec.get("hpc", 0),
                                       "mixed": ec.get("mixed", 0), "unknown": ec.get("unknown", 0)}, indent=1, sort_keys=True))
    base_units = plan(rows, "own-only", envs, ns.field, primary, compared)["units"]            # the units, whichever variants run: the bytes counts do not depend on the layout reads
    bu = bytes_units_summary(base_units, compared)
    bup = L.layout_dir(seal) / "bytes_units.json"
    if not bup.exists():
        L.write_atomic(bup, json.dumps(bu, indent=1, sort_keys=True))
    info = {"variants": {}, "beside_tables": 0, "bytes_units_qualifying": bu["primary_qualifying"]}
    plans = {v: plan(rows, v, envs, ns.field, primary, compared) for v in variants}
    for v in variants:                       # refused before anything is made: a variant that exists is never overwritten, and the other must not be started beside it
        if (L.layout_dir(seal) / v).exists():
            raise L.LayoutReadError(f"{L.layout_dir(seal) / v} exists: never overwritten (move it aside)")
    par = min(ns.parallel or 4, len(variants))
    if par > 1:
        # The analyses are independent (each reads the same frozen inputs and writes its own directory): one process each, forked so that they inherit the inputs. A failing one is raised
        # when its result is read, after the others have finished.
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        global _CTX
        _CTX = (seal, base, snap, rows, ns, cfg, bootstrap, plans)
        with ProcessPoolExecutor(par, mp_context=multiprocessing.get_context("fork")) as ex:
            futs = {v: ex.submit(_one_in_context, v) for v in variants}
            results = {v: fu.result() for v, fu in futs.items()}
    else:
        results = {v: _one(seal, base, snap, rows, v, ns, cfg, bootstrap, plans[v]) for v in variants}
    for v in variants:
        res = results[v]
        info["variants"][v] = res
    from . import stamp
    line = stamp.header(bool(snap["final"]), snap["t"])
    envdirs = {v[4:]: L.layout_dir(seal) / v / "tables" for v in variants if v.startswith("env-") and info["variants"][v]["ran"]}
    if envdirs:
        info["beside_tables"] += len(beside_environments(base / "tables", envdirs, L.layout_dir(seal) / "environments" / "beside", line))
    info["beside_tables"] += sum(r["beside_tables"] for r in info["variants"].values())
    info["cell_day_iou_rows"] = cell_day_iou_side(seal, base, snap, cfg, bootstrap)
    info["coverage_finished"] = coverage_finished_soft(seal, base, snap, cfg, bootstrap)
    return info


_CTX: tuple | None = None


def _one_in_context(v: str) -> dict:
    seal, base, snap, rows, ns, cfg, bootstrap, plans = _CTX
    return _one(seal, base, snap, rows, v, ns, cfg, bootstrap, plans[v])


def _one(seal: Path, base: Path, snap: dict, lrows: list[dict], variant: str, ns, cfg, bootstrap: bool, pl: dict) -> dict:
    import tempfile
    import os
    import pandas as pd
    from icsa.analysis import adapter, config as cfgmod, inspection as INS, overhead as OV
    from icsa.analysis.run import run_all
    from . import stamp
    from .guard import WriteGuard, captured

    out = L.layout_dir(seal) / variant
    if out.exists():
        raise L.LayoutReadError(f"{out} exists: never overwritten (move it aside)")
    drop = pl["drop_runs"]
    rows = adapter.load_jsonl(base / "pipeline" / "scored_rows.jsonl")
    scored_keys = {(r.block, r.run.key()) for r in rows}
    if {(x["block"], x["run"]) for x in lrows} - scored_keys:
        raise L.LayoutReadError("layout_read.csv names runs the analysis' scored rows do not hold: it is not of this seal")
    kept = [r for r in rows if (r.block, r.run.key()) not in drop]
    out.mkdir(mode=0o700)
    for d in ("inputs", "tables", ".captured", ".tmp"):
        (out / d).mkdir(mode=0o700)
    with open(out / "units.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["block_group", "instance", "layout", "model", "n_runs", "environment", "status", "reason", "runs_without_value", "bytes_measured", "bytes_measured_lenient"])
        for u in pl["units"]:
            w.writerow([*u["unit"], u["n_runs"], u["environment"], u["status"], u["reason"], u["runs_without_value"], int(u["bytes_measured"]), int(u["bytes_measured_lenient"])])
    with open(out / "units_by_model.csv", "w", newline="") as fh:
        ub = units_by_model(pl["units"], variant)
        w = csv.DictWriter(fh, fieldnames=list(ub[0]) if ub else ["model"], lineterminator="\n")
        w.writeheader()
        w.writerows(ub)
    with open(out / "dropped_runs.csv", "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["block", "run_key", "reason"])
        for (b, k), why in sorted(drop.items()):
            w.writerow([b, f"{b}__{k}", why])
    meta = {"variant": variant, "base": base.name, "field": ns.field, "rows_kept": len(kept), "rows_dropped": len(rows) - len(kept), "units": len(pl["units"]),
            "units_left": len(pl["drop_units"]), "snapshot_final": snap["final"], "snapshot_t": snap["t"], "ran": bool(kept)}
    if not kept:                                  # no unit qualifies: there is nothing to analyse, and that is a result of its own
        L.write_atomic(out / "own_only.json", json.dumps({**meta, "skipped": "no unit is left for this variant"}, indent=1, sort_keys=True))
        return {"ran": False, "beside_tables": 0}
    os.environ.update(TMPDIR=str(out / ".tmp"), MPLCONFIGDIR=str(out / ".tmp" / "mpl"), XDG_CACHE_HOME=str(out / ".tmp" / "cache"), PYTHONDONTWRITEBYTECODE="1")
    tempfile.tempdir = str(out / ".tmp")
    guard = WriteGuard([L.layout_dir(seal)]).install()
    try:
        d = set(drop)
        n_infra = filter_infra(base / "pipeline" / "infra.json", out / "inputs" / "infra.json", d, pl["drop_units"], pl["primary"])
        causes = pd.read_csv(base / "pipeline" / "causes.csv")
        causes = causes[[(b, k) not in d for b, k in zip(causes["block"], causes["run_key"])]]
        flags = pd.read_csv(base / "pipeline" / "cause_flags.csv")
        flags = flags[[(b, k) not in d for b, k in zip(flags["block"], flags["run_key"])]]
        inputs = snap.get("inputs") or {}
        overhead = ns.overhead or inputs.get("overhead", "none")
        fidelity = ns.fidelity_rows or inputs.get("fidelity_rows", "none")
        labels = inputs.get("inspection_labels", "none")
        cfg = cfg or cfgmod.load(ns.config)
        ov = OV.OverheadTable.absent() if overhead == "none" else OV.load(overhead, cfg)
        fid = [] if fidelity == "none" else adapter.load_fidelity_rows(fidelity)
        if labels == "none":
            ins = INS.InspectionInput.not_run()
        else:
            cov = seal / "frozen" / "inspection-coverage.jsonl"
            filter_jsonl(Path(labels), out / "inputs" / "inspection-labels.jsonl", d)
            if cov.is_file():
                filter_jsonl(cov, out / "inputs" / "inspection-coverage.jsonl", d)
            ins = INS.load(out / "inputs" / "inspection-labels.jsonl", out / "inputs" / "inspection-coverage.jsonl" if cov.is_file() else None)
        with captured(out / ".captured" / "analysis.log"):
            run_all(kept, out / "tables", cfg, causes, bootstrap=bootstrap, fidelity_rows=fid, h3_table=pd.read_csv(ns.h3_table) if ns.h3_table else None,
                    infra=out / "inputs" / "infra.json", overhead=ov, inspection=ins, cause_flags=flags)
        line = stamp.header(bool(snap["final"]), snap["t"])
        stamp.stamp_tables(out / "tables", line)
        stamp.check_tables(out / "tables", line)
        written = beside(base / "tables", out / "tables", out / "beside", line) if variant.startswith("own-only") else []
        if variant == "bytes-measured":
            written = h2_beside(base / "tables", out / "tables", out / "beside", line)
        meta.update(infra_analysed_dropped=n_infra, beside=written, inputs={"overhead": overhead, "fidelity_rows": fidelity, "inspection_labels": labels, "h3_table": ns.h3_table})
        L.write_atomic(out / "own_only.json", json.dumps(meta, indent=1, sort_keys=True))
    finally:
        guard.off()
    return {"ran": True, "beside_tables": len(written)}
