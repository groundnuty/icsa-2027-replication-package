#!/usr/bin/env python3
"""The paper's results-section exhibits of an interim snapshot (science, #34, 5 Nov 16:51Z), built on the snapshot's OWN sealed outputs.

    paper_exhibits.py <seal dir> [--out-dir DIR] [--analysis auto|out-coded|out] [--frozen-tree DIR] [--parts fidelity,models,causes]
                      [--map fault_type=Paper row] [--label option=Label] [--smallest-effect-sides both|plus]

Nothing is recomputed: every number is read from a table the snapshot already wrote. The frozen method and every registered table stay as they are.
Writes under <seal>/exhibits/ (mode 700; files 600), or --out-dir:

  fidelity_per_fault_type.csv / .md   recall and precision per fault type, per option x layout x record x condition, with tested or not
                                      (source: frozen/fault/h3_table.csv, whose fault_type column carries the per-type rows)
  models_forest.csv / fig_models.pdf  S1 omission contrasts T-M and D-M with 95% intervals per model, in points, a dashed line at the 10-point smallest effect
                                      (source: <analysis>/tables/h4_per_model_effects.csv)
  causes_breakdown.csv / fig_causes.pdf   finished omitting runs by cause (instrument-labelled runs: <analysis>/pipeline/causes.csv; runs the coders resolved to omitting:
                                      <seal>/coder_replay/coder_causes.csv, `cause_window_rule`), and apart from them the runs that ended without a report or at a cap
                                      (<analysis>/tables/cause_breakdown.csv, classes unfinished:*). Cross-checked against the registered cause_breakdown, see `checks`.
  exhibits.meta.json                  sources, analysis used, per-part status and seconds, checks (names and counts of cells only, no value)

A table is never overwritten: a part whose output exists is refused. stdout is a line per part (rows, files, seconds) and the checks line; no value, no count by option.
Exit: 0 clean | 2 every part refused | 3 partial (a part skipped, degraded or failed; the others stand) | 9 nothing could be produced.
Errors raised here name columns and files only, never data; any other exception is reduced to its type and location.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import textwrap
import time
import traceback
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np    # noqa: E402
import pandas as pd    # noqa: E402

try:    # a plain script on the run host; the frozen tree is only read for config and the observability classification
    import tomllib    # noqa: E402
except ImportError:    # pragma: no cover
    tomllib = None

# ----------------------------------------------------------------------------------------------------------------------------- what the paper calls things
# One mapping for all three exhibits (T is "A" in the paper). Change here, or with --label option=Label.
OPTION_LABEL = {"T": "A", "T-unpaginated": "A, complete listing"}      # science, #34 17:23Z
OPTION_ORDER = ["T", "T-unpaginated", "D", "M"]
LAYOUT_ORDER = ["S1", "S2"]
MINUS = "−"

# The paper's fidelity rows -> the fault types behind each (science, #34 17:06Z): `file_range_skip` (a contiguous run of WHOLE files) has its own row; every other fault type is printed too, with an
# EMPTY paper_row. The matrix has no fault that leaves part of a daily file unread in S1, so there is no such row. Change here or with --map fault_type=Paper row.
PAPER_ROWS = [
    ("whole files skipped (S1)", ["whole_file_skip"]),
    ("a run of whole files skipped (S1)", ["file_range_skip"]),
    ("chunks or time steps skipped (S2)", ["chunk_skip", "chunk_range_skip"]),
    ("header-only reads (S1, S2)", ["header_only"]),
    ("full read, partial use (S1, S2)", ["full_read_partial_use"]),
]
NO_PAPER_ROW = ""

MODEL_ORDER = ["DeepSeek-V4-Flash-0731", "GLM-5.3-Flash", "Gemma-4-31B", "Qwen3-Coder-30B-A3B", "Qwen3.8-27B", "claude-haiku-5-5", "claude-sonnet-5-5"]
FOREST_CONTRASTS = ["T-M", "D-M"]
SMALLEST_EFFECT_POINTS = 10.0

# The cause codebook's order (icsa/causes/codebook.py); anything else is kept, after these, as `other:<name>`.
CAUSE_ORDER = ["infra_failure", "time_cap", "turn_cap", "token_budget", "output_cap", "run_error", "truncated_listing", "wrong_subset_period", "wrong_subset_baseline",
               "wrong_subset_region", "skipped_or_partial_read", "read_not_used", "early_stop", "analysis_error_on_covered_data", "unknown"]
NOT_CODED = "not coded (coders' extent only)"
TERMINATION_ORDER = ["time_cap", "turn_cap", "token_budget", "output_cap", "error", "report"]
# icsa.records.Termination: `report` is a run that ended by its final message without a valid report (a finished run has one); `error` a harness or model error that is not an infra failure.
TERMINATION_LABEL = {"report": "final message, no valid report", "error": "harness or model error", "time_cap": "time cap", "turn_cap": "turn cap", "token_budget": "token budget",
                     "output_cap": "output cap"}


def category_label(panel: str, c: str) -> str:
    return TERMINATION_LABEL.get(c, c.replace("_", " ")) if panel == "ended_without_report_or_at_cap" else c.replace("_", " ")
DEFAULT_PRIMARY_BLOCKS = ["main", "pagination"]
DEFAULT_OPTIONS = ["T", "D", "M", "T-unpaginated"]

# fault-type cell columns of frozen/fault/h3_table.csv
H3_REQUIRED = ["option", "layout", "record", "condition", "fault_type", "subset", "tested", "n_faulted", "n_control", "recall", "recall_lo", "recall_hi",
               "precision", "precision_lo", "precision_hi", "status"]
H3_OPTIONAL = ["false_alarm", "masked_share", "served_unit_share", "n_per_instance"]
CELL = ["option", "layout", "record", "condition"]

RC_OK, RC_REFUSED, RC_PARTIAL, RC_FAILED = 0, 2, 3, 9


class ExhibitError(Exception):
    """An error whose text names columns and files only: it is safe to print."""


# ----------------------------------------------------------------------------------------------------------------------------- reading
def read_table(path: Path) -> tuple[pd.DataFrame, str | None]:
    """A snapshot table: `# snapshot final=.. t=..` first line (tables under out*/tables), or the header at once (frozen/fault/h3_table.csv). The stamp is detected, never assumed."""
    if not path.is_file():
        raise ExhibitError(f"missing file: {path.name}")
    with open(path, "r", encoding="utf-8") as f:
        first = f.readline()
    stamp = first.rstrip("\r\n") if first.startswith("# snapshot") else None
    try:
        df = pd.read_csv(path, skiprows=1 if stamp else 0)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()
    return df, stamp


def need(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ExhibitError(f"{name}: columns missing: {missing}")


def as_bool(s: pd.Series) -> pd.Series:
    m = {"true": True, "false": False, "1": True, "0": False}
    return s.map(lambda v: v if isinstance(v, (bool, np.bool_)) else m.get(str(v).strip().lower(), False)).astype(bool)


def stamp_of(analysis: Path, seal: Path) -> str:
    tdir = analysis / "tables"
    if tdir.is_dir():
        for p in sorted(tdir.glob("*.csv")):
            with open(p, "r", encoding="utf-8") as f:
                first = f.readline()
            if first.startswith("# snapshot"):
                return first.rstrip("\r\n")
    try:
        s = json.loads((analysis / "SNAPSHOT.json").read_text())
        return f"# snapshot final={str(s.get('final', 'unknown')).lower()} t={s.get('t', 'unknown')}"
    except Exception:
        return "# snapshot final=unknown t=unknown"


def analysis_complete(p: Path) -> bool:
    """`tables/manifest.json` is the LAST file icsa.analysis.run writes (after every table and the pair marks): a directory with tables and no manifest is an analysis that stopped
    half way (the driver's URC=10), and its tables are not read."""
    return (p / "tables" / "manifest.json").is_file()


CODED = ("out-coded", "out-coded-kaug")        # the analyses that carry the coders' decisions (lane-snap6, 6 Nov: out-coded-kaug is the K-augmented PRIMARY coded set, science #34 03:30Z)


def pick_analysis(seal: Path, which: str) -> tuple[Path, str]:
    if which in ("out", "out-coded", "out-kaug", "out-coded-kaug"):
        if not analysis_complete(seal / which):
            raise ExhibitError(f"{which}/tables/manifest.json does not exist: that analysis is not complete")
        return seal / which, ""
    try:        # the seal says which coded set is the primary one (PRIMARY.json, written by the driver); only a complete directory is taken
        import json as _json
        hint = _json.loads((seal / "PRIMARY.json").read_text()).get("primary_coded_tables")
        if hint in CODED and analysis_complete(seal / hint):
            return seal / hint, "" if hint == "out-coded" else f"PRIMARY.json names {hint} as the primary coded tables"
    except (OSError, ValueError):
        pass
    if analysis_complete(seal / "out-coded"):
        return seal / "out-coded", ""
    if analysis_complete(seal / "out"):
        why = "out-coded has no complete tables (no tables/manifest.json)" if (seal / "out-coded").exists() else "there is no out-coded"
        return seal / "out", f"{why}: the exhibits read out"
    raise ExhibitError("neither out-coded nor out has complete tables (tables/manifest.json)")


def frozen_config(frozen_tree: Path | None) -> dict:
    """Primary blocks, analysed options and the pagination option, read from the frozen analysis' own config; the defaults say so in the meta."""
    cfg = {"primary_blocks": list(DEFAULT_PRIMARY_BLOCKS), "options": list(DEFAULT_OPTIONS), "source": "defaults"}
    if frozen_tree is None or tomllib is None:
        return cfg
    p = frozen_tree / "icsa" / "analysis" / "preregistered.toml"
    try:
        c = tomllib.loads(p.read_text())
        pag = c["pagination"]["option"]
        cfg = {"primary_blocks": list(c["blocks"]["primary"]), "options": [*c["inference"]["main_options"], pag], "source": "preregistered.toml"}
    except Exception:
        cfg["failed_to_read"] = "preregistered.toml"       # the defaults stand, and the causes part says so
    return cfg


def option_label(o: str) -> str:
    return OPTION_LABEL.get(o, o)


def ordered(values, order: list[str]) -> list[str]:
    vs = list(dict.fromkeys(values))
    return [v for v in order if v in vs] + sorted(v for v in vs if v not in order)


def fmt(x) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) or pd.isna(x) else f"{float(x):.2f}"


def with_ci(v, lo, hi) -> str:
    return "–" if pd.isna(v) else f"{float(v):.2f} ({fmt(lo)}–{fmt(hi)})"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, df: pd.DataFrame, stamp: str) -> None:
    write_atomic(path, stamp + "\n" + df.to_csv(index=False, lineterminator="\n"))


class Staged:
    """A part's files are written into `.stage-<part>/` and moved in together at its end: a part killed at the time box leaves no half-written pair, so a rerun by hand redoes
    exactly the parts that did not finish (the finished ones are refused, never overwritten). Only this stage's own leftover staging files are removed."""

    def __init__(self, out: Path, part: str):
        self.out, self.dir = out, out / f".stage-{part}"
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir.mkdir(mode=0o700)

    def path(self, name: str) -> Path:
        return self.dir / name

    def commit(self, names: list[str]) -> None:
        for n in names:
            os.replace(self.dir / n, self.out / n)
        shutil.rmtree(self.dir, ignore_errors=True)


def finish(st: Staged, part: str, names: list[str], res: dict) -> dict:
    """The part's result (status, checks, notes) is written beside its files and moves in with them: a rerun that refuses the finished part keeps its record."""
    write_atomic(st.path(f"{part}.meta.json"), json.dumps(res, indent=1, default=str))
    st.commit(names + [f"{part}.meta.json"])
    return res


def refuse_if_exists(out: Path, names: list[str]) -> None:
    have = [n for n in names if (out / n).exists()]
    if have:
        raise FileExistsError(f"already in {out.name}/: {have}; a snapshot is never overwritten: move them aside")


# ----------------------------------------------------------------------------------------------------------------------------- 1. fidelity per fault type
def observability_lookup(frozen_tree: Path | None):
    """classify(fault, layout, option, record, condition) of the frozen observability table, or None when the frozen tree cannot be imported. A lookup of a
    class written by hand before any run (icsa/faults/observability.py), not a computation on data."""
    if frozen_tree is None:
        return None
    try:
        sys.path.insert(0, str(frozen_tree))
        from icsa.faults.observability import classify    # noqa: E402
        from icsa.faults.records.base import Record    # noqa: E402
        from icsa.faults.scenarios import Condition, Fault    # noqa: E402
        from icsa.records import Layout, Option    # noqa: E402
    except Exception:
        return None
    cache: dict = {}

    def get(f: str, layout: str, opt: str, rec: str, cond: str) -> str:
        k = (f, layout, opt, rec, cond)
        if k not in cache:
            try:
                cache[k] = classify(Fault(f), Layout(layout), Option(opt), Record(rec), Condition(cond)).obs.value
            except Exception:
                cache[k] = "unknown"
        return cache[k]
    return get


def paper_row_map(overrides: dict[str, str]) -> dict[str, str]:
    m = {f: row for row, faults in PAPER_ROWS for f in faults}
    m.update(overrides)
    return m


def fidelity_table(h3: pd.DataFrame, fmap: dict[str, str], obs) -> pd.DataFrame:
    need(h3, H3_REQUIRED, "h3_table.csv")
    t = h3.copy()
    for c in H3_OPTIONAL:
        if c not in t.columns:
            t[c] = np.nan
    t["tested"] = as_bool(t["tested"])
    for c in ("option", "layout", "record", "condition", "fault_type", "subset", "status"):
        t[c] = t[c].astype(str)
    cellrow = t[(t.fault_type == "all") & (t.subset == "observable")].drop_duplicates(CELL)
    cellrow = cellrow[[*CELL, "tested", "status"]].rename(columns={"tested": "cell_tested", "status": "cell_status"})
    rows = t[t.subset == "all"].copy()
    rows = rows.merge(cellrow, on=CELL, how="left")
    rows["cell_tested"] = rows["cell_tested"].map(lambda v: "" if pd.isna(v) else ("yes" if bool(v) else "no"))
    rows["cell_status"] = rows["cell_status"].fillna("")
    rows["paper_row"] = rows["fault_type"].map(lambda f: NO_PAPER_ROW if f == "all" else fmap.get(f, NO_PAPER_ROW))
    if obs is None:
        rows["fault_observability"] = "unknown"
    else:
        rows["fault_observability"] = [("" if f == "all" else obs(f, l, o, r, c))
                                       for f, l, o, r, c in zip(rows.fault_type, rows.layout, rows.option, rows.record, rows.condition)]
    tested_set = {"observable": "yes", "observable_per_instance": "per_instance", "unobservable_by_design": "no", "not_applicable": "no", "unknown": "unknown"}
    rows["fault_in_tested_subset"] = rows["fault_observability"].map(lambda v: "" if v == "" else tested_set.get(v, "unknown"))
    rows["option_label"] = rows["option"].map(option_label)
    paper_order = [r for r, _ in PAPER_ROWS]
    rows["_p"] = rows["paper_row"].map(lambda r: paper_order.index(r) if r in paper_order else len(paper_order))
    rows["_a"] = (rows["fault_type"] == "all").astype(int)                  # the `all faults` row last within its group
    rows["_o"] = rows["option"].map(lambda o: OPTION_ORDER.index(o) if o in OPTION_ORDER else len(OPTION_ORDER))
    rows["_l"] = rows["layout"].map(lambda o: LAYOUT_ORDER.index(o) if o in LAYOUT_ORDER else len(LAYOUT_ORDER))
    rows = rows.sort_values(["_p", "_a", "fault_type", "_o", "_l", "record", "condition"], kind="stable")
    cols = ["paper_row", "fault_type", "option", "option_label", "layout", "record", "condition", "fault_observability", "fault_in_tested_subset", "cell_tested", "cell_status",
            "tested", "status", "n_faulted", "n_control", "recall", "recall_lo", "recall_hi", "precision", "precision_lo", "precision_hi", "false_alarm",
            "masked_share", "served_unit_share", "n_per_instance"]
    return rows[cols].reset_index(drop=True)


FIDELITY_FOOT = """\
How to read it. Source: `frozen/fault/h3_table.csv` (the registered H3 matrix); nothing here is recomputed. Condition `cold` only; the other conditions (M's warm_buffer, prefetch_on) and the `all faults` rows are in the CSV.
- **tested**: the fault type is in the tested subset of the cell (observable by design in that cell; `per_instance` = only the runs not masked by the client count). `no` = reported only.
  The cell's own H3 status (pass / fail / incomplete / not_testable) is `cell_status` in the CSV; per-type rows are never a verdict.
- **recall** is over every faulted run of the type, unobservable and masked ones included (the tested row of the cell is over the observable ones only), so a low recall where `tested` is `no` is by design.
- **precision** divides by the flags of the type's runs plus the WHOLE cell's control false alarms: one control alarm lowers every type's precision of that cell. The rows are not a partition.
- Intervals are Wilson 95%. A dash is undefined (no faulted run, or nothing flagged).
"""


def fidelity_markdown(rows: pd.DataFrame, stamp: str, fmap: dict[str, str]) -> str:
    d = rows[(rows.condition == "cold") & (rows.fault_type != "all")]
    parts = [stamp, "", "# Fidelity per fault type", ""]
    heads = ["option", "layout", "record", "fault type", "observable by design", "tested", "recall (95%)", "precision (95%)", "runs faulted / control"]

    def block(title: str, g: pd.DataFrame, empty_note: str = "") -> None:
        parts.extend([f"## {title}", ""])
        if g.empty:
            parts.extend([empty_note or "no row in this snapshot.", ""])
            return
        body = [[r.option_label, r.layout, r.record, r.fault_type, (r.fault_observability or "unknown").replace("_", " "), r.fault_in_tested_subset or "unknown", with_ci(r.recall, r.recall_lo, r.recall_hi),
                 with_ci(r.precision, r.precision_lo, r.precision_hi), f"{int(r.n_faulted) if pd.notna(r.n_faulted) else 0} / {int(r.n_control) if pd.notna(r.n_control) else 0}"]
                for r in g.itertuples()]
        parts.extend([md_table(heads, body), ""])
    for row, faults in PAPER_ROWS:
        block(row, d[d.paper_row == row])
    other = d[d.paper_row == NO_PAPER_ROW]
    if len(other):
        block("Other fault types (no paper row; the `all faults` rows and the other conditions are in the CSV)", other)
    parts.extend(["## Notes", "", FIDELITY_FOOT])
    return "\n".join(parts)


def part_fidelity(seal: Path, out: Path, stamp: str, args, obs) -> dict:
    t0 = time.time()
    names = ["fidelity_per_fault_type.csv", "fidelity_per_fault_type.md"]
    refuse_if_exists(out, names)
    h3, _ = read_table(seal / "frozen" / "fault" / "h3_table.csv")
    fmap = paper_row_map(args.map)
    note = ""
    if h3.empty or "fault_type" not in h3.columns:
        raise ExhibitError("h3_table.csv has no rows or no fault_type column: no fidelity table at this snapshot")
    rows = fidelity_table(h3, fmap, obs)
    st = Staged(out, "fidelity")
    write_csv(st.path(names[0]), rows, stamp)
    write_atomic(st.path(names[1]), fidelity_markdown(rows, stamp, fmap))
    status = "ok" if (obs is not None or args.no_observability) else "degraded"
    if obs is None and not args.no_observability:
        note = "observability class unavailable (frozen tree not importable): fault_observability is `unknown`"
    return finish(st, "fidelity", names, {"status": status, "rows": int(len(rows)), "files": 2, "seconds": round(time.time() - t0, 2), "note": note})


# ----------------------------------------------------------------------------------------------------------------------------- 2a. models: forest plot
def pdf_checks(path: Path) -> dict:
    data = path.read_bytes()
    return {"is_pdf": data[:5] == b"%PDF-", "has_image": b"/Subtype /Image" in data or b"/Subtype/Image" in data,
            "has_type3_font": b"/Subtype /Type3" in data or b"/Subtype/Type3" in data}


def set_plot_defaults():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
                         "legend.fontsize": 7, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.spines.top": False, "axes.spines.right": False})
    return plt


def contrast_label(c: str) -> str:
    a, b = c.split("-", 1)
    return f"{option_label(a)} {MINUS} {option_label(b)}"


def forest_frame(h4: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    need(h4, ["outcome", "layout", "contrast", "model", "effect", "ci_lo", "ci_hi", "tier"], "h4_per_model_effects.csv")
    d = h4[(h4.outcome.astype(str) == "omission") & (h4.layout.astype(str) == "S1") & (h4.contrast.astype(str).isin(FOREST_CONTRASTS))].copy()
    present = [m for m in dict.fromkeys(d.model.astype(str))]
    extra = [m for m in present if m not in MODEL_ORDER]
    absent = [m for m in MODEL_ORDER if m not in present]
    models = MODEL_ORDER + extra
    recs = []
    for m in models:
        for c in FOREST_CONTRASTS:
            g = d[(d.model.astype(str) == m) & (d.contrast.astype(str) == c)]
            r = g.iloc[0] if len(g) else None
            pts = lambda col: (float(r[col]) * 100.0 if r is not None and pd.notna(r[col]) else np.nan)    # noqa: E731
            recs.append({"model": m, "tier": ("" if r is None or pd.isna(r["tier"]) else str(r["tier"])), "outcome": "omission", "layout": "S1", "contrast": c,
                         "contrast_label": contrast_label(c), "effect_points": pts("effect"), "ci_lo_points": pts("ci_lo"), "ci_hi_points": pts("ci_hi"),
                         "pooled_effect_points": pts("pooled_effect") if "pooled_effect" in d.columns else np.nan,
                         "has_estimate": bool(r is not None and pd.notna(r["effect"]))})
    return pd.DataFrame(recs), extra, absent


def draw_forest(site_g: pd.DataFrame, path: Path, sides: str) -> dict:
    plt = set_plot_defaults()
    models = list(dict.fromkeys(site_g.model))
    ypos = {m: len(models) - 1 - i for i, m in enumerate(models)}
    lim = max(SMALLEST_EFFECT_POINTS * 1.5, float(np.nanmax(np.abs(site_g[["ci_lo_points", "ci_hi_points", "effect_points"]].to_numpy(dtype=float)))) * 1.1
              if site_g[["ci_lo_points", "ci_hi_points", "effect_points"]].notna().any().any() else SMALLEST_EFFECT_POINTS * 1.5)
    fig, axes = plt.subplots(1, len(FOREST_CONTRASTS), figsize=(7.0, 0.42 * len(models) + 1.3), sharey=True, sharex=True)
    for ax, c in zip(axes, FOREST_CONTRASTS):
        g = site_g[site_g.contrast == c]
        ax.axvline(0, color="0.25", lw=0.8)
        for x in ([SMALLEST_EFFECT_POINTS, -SMALLEST_EFFECT_POINTS] if sides == "both" else [SMALLEST_EFFECT_POINTS]):
            ax.axvline(x, color="0.45", lw=0.9, ls=(0, (4, 3)))
        for r in g.itertuples():
            y = ypos[r.model]
            if r.has_estimate and pd.notna(r.ci_lo_points) and pd.notna(r.ci_hi_points):
                ax.errorbar(r.effect_points, y, xerr=[[r.effect_points - r.ci_lo_points], [r.ci_hi_points - r.effect_points]], fmt="o", ms=4, color="#1f4e79", ecolor="#1f4e79",
                            elinewidth=1.1, capsize=2.2)
            elif r.has_estimate:
                ax.plot(r.effect_points, y, "o", ms=4, color="#1f4e79")
            else:
                ax.text(0, y, "no estimate", ha="center", va="center", fontsize=6.5, color="0.5")
        ax.set_title(g.contrast_label.iloc[0])
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-0.7, len(models) - 0.3)
        ax.set_xlabel("difference in omission rate (percentage points)")
        ax.grid(axis="x", color="0.9", lw=0.5)
        ax.set_axisbelow(True)
    axes[0].set_yticks([ypos[m] for m in models])
    axes[0].set_yticklabels(models)
    axes[0].set_ylabel("model")
    fig.tight_layout()
    assert len(axes[0].get_yticks()) == len(models), "forest plot: one y tick per model row"
    assert all(a.get_xlabel() for a in axes) and axes[0].get_ylabel(), "forest plot: axes labelled"
    fig.savefig(path, format="pdf", metadata={"Creator": "paper_exhibits.py", "CreationDate": None})
    plt.close(fig)
    return {"rows": len(models)}


def part_models(analysis: Path, out: Path, stamp: str, args) -> dict:
    t0 = time.time()
    names = ["models_forest.csv", "fig_models.pdf"]
    refuse_if_exists(out, names)
    h4, _ = read_table(analysis / "tables" / "h4_per_model_effects.csv")
    if h4.empty:
        raise ExhibitError("h4_per_model_effects.csv has no rows: no forest plot at this snapshot")
    site_g, extra, absent = forest_frame(h4)
    site_g["source_analysis"] = analysis.name
    st = Staged(out, "models")
    write_csv(st.path(names[0]), site_g, stamp)
    info = draw_forest(site_g, st.path(names[1]), args.smallest_effect_sides)
    chk = pdf_checks(st.path(names[1]))
    bad = [k for k in ("has_image", "has_type3_font") if chk[k]] + ([] if chk["is_pdf"] else ["not_a_pdf"])
    status = "ok" if not (bad or extra or absent) else "degraded"
    notes = []
    detail = {}
    if extra or absent:        # which models: data-dependent, so the meta only (stdout is copied into the snapshot log)
        notes.append("a model has no row in the table, or a model beyond the seven is in it: which, in exhibits.meta.json")
        detail = {"models_without_row_drawn_empty": absent, "models_beyond_the_seven_drawn_as_extra_rows": extra}
    if bad:
        notes.append(f"pdf checks failed: {bad}")
    return finish(st, "models", names, {"status": status, "rows": int(len(site_g)), "files": 2, "seconds": round(time.time() - t0, 2), "pdf": chk, "figure_rows": info["rows"], "note": "; ".join(notes), "detail": detail})


# ----------------------------------------------------------------------------------------------------------------------------- 2b. causes
def split_run_key(keys: pd.Series) -> pd.DataFrame:
    """run_key = <instance>__<option>__<layout>__<model>__s<seed> (icsa.records.RunId.key): option and layout from the right."""
    parts = keys.astype(str).str.rsplit("__", n=4, expand=True)
    if parts.shape[1] != 5:
        raise ExhibitError("run_key: not of the form instance__option__layout__model__s<seed>")
    parts.columns = ["instance", "option", "layout", "model", "seed"]
    return parts


def cell_counts(df: pd.DataFrame) -> pd.Series:
    return df.groupby(["option", "layout"]).size() if len(df) else pd.Series(dtype=int)


def compare_cells(name: str, a: pd.Series, b: pd.Series) -> dict:
    cells = a.index.union(b.index)
    diff = int(((a.reindex(cells, fill_value=0)) != (b.reindex(cells, fill_value=0))).sum()) if len(cells) else 0
    return {"name": name, "ok": diff == 0, "cells_differing": diff, "cells": int(len(cells))}


def causes_inputs(analysis: Path, seal: Path, cfg: dict, use_coders: bool):
    cb, _ = read_table(analysis / "tables" / "cause_breakdown.csv")
    need(cb, ["option", "layout", "class", "n"], "cause_breakdown.csv")
    cb["class"] = cb["class"].astype(str)
    pipe, _ = read_table(analysis / "pipeline" / "causes.csv")
    need(pipe, ["block", "run_key", "cause", "population"], "pipeline/causes.csv")
    pipe = pd.concat([pipe, split_run_key(pipe.run_key)[["option", "layout"]]], axis=1) if len(pipe) else pipe.assign(option=pd.Series(dtype=str), layout=pd.Series(dtype=str))
    ooc = set()
    p = analysis / "tables" / "out_of_cohort_runs.csv"
    if p.is_file():
        o, _ = read_table(p)
        if len(o) and "run_key" in o.columns:
            ooc = set(o.run_key.astype(str))       # kept and reported by the analysis, in no table of omission: left out here, from BOTH files
    pipe = pipe[pipe.block.astype(str).isin(cfg["primary_blocks"]) & pipe.option.isin(cfg["options"]) & ~pipe.run_key.astype(str).isin(ooc)]
    coders = None
    cpath = seal / "coder_replay" / "coder_causes.csv"
    if use_coders and cpath.is_file():
        coders, _ = read_table(cpath)
        if len(coders):
            need(coders, ["block", "run_key", "coded", "cause", "cause_window_rule"], "coder_causes.csv")
            coders = coders.copy()
            coders["option"] = split_run_key(coders.run_key)["option"].values
            coders["layout"] = split_run_key(coders.run_key)["layout"].values
            coders = coders[coders.block.astype(str).isin(cfg["primary_blocks"]) & coders.option.isin(cfg["options"]) & ~coders.run_key.astype(str).isin(ooc)]
        else:
            coders = pd.DataFrame(columns=["block", "run_key", "coded", "cause", "cause_window_rule", "option", "layout"])
    return cb, pipe, coders


def causes_checks(cb: pd.DataFrame, pipe: pd.DataFrame, coders, analysis: Path) -> list[dict]:
    out = []
    pop = pipe[pipe.population.astype(str).isin(["omitting", "unfinished"])]
    cause_rows = cb[cb["class"].str.startswith("cause:")]
    if len(cause_rows):
        a = pop.assign(c=pop.cause.astype(str)).groupby(["option", "layout", "c"]).size()
        b = cause_rows.assign(c=cause_rows["class"].str[len("cause:"):]).groupby(["option", "layout", "c"])["n"].sum().astype(int)
        out.append(compare_cells("causes_csv_vs_cause_breakdown_cause_rows", a, b))
    else:
        out.append({"name": "causes_csv_vs_cause_breakdown_cause_rows", "ok": None, "note": "cause_breakdown has no cause:* rows (the analysis ran without the causes)"})
    om = pipe[pipe.population.astype(str) == "omitting"]
    base_om = cb[cb["class"].isin(["omitting:disclosed", "omitting:silent"])].groupby(["option", "layout"])["n"].sum().astype(int)
    if coders is not None:
        n_c = cell_counts(coders)
        both = pd.concat([cell_counts(om), n_c], axis=1).fillna(0).sum(axis=1).astype(int) if len(om) or len(n_c) else pd.Series(dtype=int)
        out.append(compare_cells("instrument_omitting_plus_coders_vs_omitting_classes", both, base_om))
        p = analysis / "tables" / "routed_decided_complete.csv"
        if p.is_file():
            r, _ = read_table(p)
            if len(r) and "decided_omitting" in r.columns:
                # INFORMATIONAL (science, #34 21:0xZ): decided_omitting counts only runs routed to inspection (icsa/analysis/secondary.py), so it may be narrower than every run the coders
                # resolved; the check that carries the figure is instrument + coders = the registered omitting classes. It is recorded in the meta, and never degrades the part.
                out.append({**compare_cells("coders_vs_decided_omitting", n_c, r.groupby(["option", "layout"])["decided_omitting"].sum().astype(int)), "informational": True})
        keys_p = set(zip(pipe.block.astype(str), pipe.run_key.astype(str)))
        keys_c = set(zip(coders.block.astype(str), coders.run_key.astype(str))) if len(coders) else set()
        out.append({"name": "no_run_in_both_files", "ok": not (keys_p & keys_c), "cells_differing": len(keys_p & keys_c)})
    elif analysis.name in CODED:    # the omitting classes include the runs the coders resolved, whose file is missing: the two cannot agree, and that is not a finding
        out.append({"name": "instrument_omitting_vs_omitting_classes", "ok": None, "note": "not comparable: out-coded counts the coders' runs and coder_causes.csv is absent"})
    else:
        out.append(compare_cells("instrument_omitting_vs_omitting_classes", cell_counts(om), base_om))
    return out


def causes_frame(cb: pd.DataFrame, pipe: pd.DataFrame, coders) -> pd.DataFrame:
    base = cb[~cb["class"].str.startswith(("cause:", "cause_detail:", "incorrect_complete:"))]
    nn = base.groupby(["option", "layout"])["n"].sum().astype(int).rename("N")
    recs = []
    om = pipe[pipe.population.astype(str) == "omitting"]
    for (o, l, c), n in om.assign(c=om.cause.astype(str)).groupby(["option", "layout", "c"]).size().items():
        recs.append({"panel": "finished_omitting", "option": o, "layout": l, "category": c if c in CAUSE_ORDER else f"other:{c}", "source": "instrument", "n": int(n)})
    if coders is not None and len(coders):
        cc = coders.copy()
        coded = as_bool(cc["coded"])
        cat = cc["cause_window_rule"].where(cc["cause_window_rule"].notna() & (cc["cause_window_rule"].astype(str) != ""), cc["cause"]).astype(str)
        cc["category"] = np.where(coded, cat, NOT_CODED)
        for (o, l, c), n in cc.groupby(["option", "layout", "category"]).size().items():
            recs.append({"panel": "finished_omitting", "option": o, "layout": l, "category": c if (c in CAUSE_ORDER or c == NOT_CODED) else f"other:{c}", "source": "coders", "n": int(n)})
    for _, r in base[base["class"].str.startswith("unfinished:")].iterrows():
        recs.append({"panel": "ended_without_report_or_at_cap", "option": r["option"], "layout": r["layout"], "category": r["class"][len("unfinished:"):],
                     "source": "termination", "n": int(r["n"])})
    f = pd.DataFrame(recs, columns=["panel", "option", "layout", "category", "source", "n"])
    f = f.merge(nn.reset_index(), on=["option", "layout"], how="left")
    f["share_of_runs"] = f["n"] / f["N"]
    f["option_label"] = f["option"].map(option_label)
    f["category_label"] = [category_label(p, c) for p, c in zip(f.panel, f.category)]
    return f[["panel", "option", "option_label", "layout", "category", "category_label", "source", "n", "N", "share_of_runs"]]


def draw_causes(f: pd.DataFrame, cells: list[tuple[str, str]], path: Path) -> dict:
    plt = set_plot_defaults()
    from matplotlib.patches import Patch
    xs = {c: i + 0.0 for i, c in enumerate(cells)}
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 5.6), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
    palette = ["#1f4e79", "#2e86c1", "#85c1e9", "#117a65", "#52be80", "#b7950b", "#f4d03f", "#af601a", "#e59866", "#922b21", "#d98880", "#6c3483", "#bb8fce", "#566573", "#aeb6bf", "#212f3d"]

    def stack(ax, d: pd.DataFrame, cats: list[str], hatch_sources: bool) -> None:
        bottom = {c: 0.0 for c in cells}
        for k, cat in enumerate(cats):
            for src, hatch in (("instrument", None), ("termination", None), ("coders", "////")):
                g = d[(d.category == cat) & (d.source == src)]
                if g.empty:
                    continue
                vals = {(r.option, r.layout): r.share_of_runs * 100 for r in g.itertuples() if pd.notna(r.share_of_runs)}
                xv = [xs[c] for c in cells if c in vals]
                hv = [vals[c] for c in cells if c in vals]
                bv = [bottom[c] for c in cells if c in vals]
                ax.bar(xv, hv, bottom=bv, width=0.72, color=palette[k % len(palette)], edgecolor="white" if hatch is None else "0.15", linewidth=0.4, hatch=hatch)
                for c in cells:
                    if c in vals:
                        bottom[c] += vals[c]
    cats_a = [c for c in CAUSE_ORDER + [NOT_CODED] if (f[(f.panel == "finished_omitting")].category == c).any()]
    cats_a += sorted(set(f[f.panel == "finished_omitting"].category) - set(cats_a))
    cats_b = [c for c in TERMINATION_ORDER if (f[(f.panel == "ended_without_report_or_at_cap")].category == c).any()]
    cats_b += sorted(set(f[f.panel == "ended_without_report_or_at_cap"].category) - set(cats_b))
    stack(a1, f[f.panel == "finished_omitting"], cats_a, True)
    stack(a2, f[f.panel == "ended_without_report_or_at_cap"], cats_b, False)
    a1.set_ylabel("finished omitting runs\n(% of the cell's runs)")
    a2.set_ylabel("ended without a report\nor at a cap (% of the cell's runs)")
    a2.set_xticks([xs[c] for c in cells])
    a2.set_xticklabels([f"{textwrap.fill(option_label(o), 10)}\n{l}" for o, l in cells], fontsize=6.5)    # a long label wraps at its blanks
    a2.set_xlabel("option × layout")
    for ax, cats, title in ((a1, cats_a, "cause"), (a2, cats_b, "termination")):
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color="0.9", lw=0.5)
        ax.set_axisbelow(True)
        handles = [Patch(facecolor=palette[k % len(palette)], edgecolor="white", label=category_label("finished_omitting" if ax is a1 else "ended_without_report_or_at_cap", c)) for k, c in enumerate(cats)]
        if ax is a1 and (f[(f.panel == "finished_omitting") & (f.source == "coders")].shape[0]):
            handles += [Patch(facecolor="white", edgecolor="0.15", label="instrument-labelled runs"), Patch(facecolor="white", edgecolor="0.15", hatch="////", label="runs the coders resolved")]
        ax.legend(handles=handles, title=title, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, borderaxespad=0.0)
    fig.tight_layout()
    assert a1.get_ylabel() and a2.get_ylabel() and a2.get_xlabel(), "causes figure: axes labelled"
    fig.savefig(path, format="pdf", metadata={"Creator": "paper_exhibits.py", "CreationDate": None}, bbox_inches="tight")
    plt.close(fig)
    return {"bars": len(cells)}


def part_causes(seal: Path, analysis: Path, out: Path, stamp: str, args, cfg: dict) -> dict:
    t0 = time.time()
    names = ["causes_breakdown.csv", "fig_causes.pdf"]
    refuse_if_exists(out, names)
    use_coders = analysis.name in CODED
    cb, pipe, coders = causes_inputs(analysis, seal, cfg, use_coders)
    notes = []
    if use_coders and coders is None:
        notes.append("coder_replay/coder_causes.csv is absent: the runs the coders resolved to omitting are NOT in the bars")
    if not use_coders:
        notes.append("analysis is `out`: no coders' labels, so no coder rows")
    if cfg.get("failed_to_read"):
        notes.append(f"{cfg['failed_to_read']} could not be read: primary blocks and options are the script's defaults")
    f = causes_frame(cb, pipe, coders)
    checks = causes_checks(cb, pipe, coders, analysis)
    f["source_analysis"] = analysis.name
    st = Staged(out, "causes")
    write_csv(st.path(names[0]), f, stamp)
    base = cb[~cb["class"].str.startswith(("cause:", "cause_detail:", "incorrect_complete:"))]
    cells = [(o, l) for o in ordered(base.option.astype(str), OPTION_ORDER) for l in ordered(base.layout.astype(str), LAYOUT_ORDER) if ((base.option == o) & (base.layout == l)).any()]
    if not cells:
        raise ExhibitError("cause_breakdown.csv has no option x layout cell")
    draw_causes(f, cells, st.path(names[1]))
    chk = pdf_checks(st.path(names[1]))
    bad = [k for k in ("has_image", "has_type3_font") if chk[k]] + ([] if chk["is_pdf"] else ["not_a_pdf"])
    failed = [c["name"] for c in checks if c.get("ok") is False and not c.get("informational")]
    status = "ok" if not (bad or failed or notes) else "degraded"
    if bad:
        notes.append(f"pdf checks failed: {bad}")
    if failed:
        notes.append(f"checks mismatch: {failed}")
    return finish(st, "causes", names, {"status": status, "rows": int(len(f)), "files": 2, "seconds": round(time.time() - t0, 2), "pdf": chk, "checks": checks, "bars": len(cells), "note": "; ".join(notes)})


# ----------------------------------------------------------------------------------------------------------------------------- driver
def safe_failure(e: BaseException) -> str:
    if isinstance(e, (ExhibitError, FileExistsError)):
        return str(e)[:300]
    if isinstance(e, KeyError):
        return f"KeyError: {str(e.args[:1])[:80]}"       # a missing column or key name
    tb = traceback.extract_tb(e.__traceback__)
    where = f"{Path(tb[-1].filename).name}:{tb[-1].lineno} in {tb[-1].name}" if tb else "?"
    return f"{type(e).__name__} at {where}"


def parse_kv(items: list[str], what: str) -> dict[str, str]:
    out = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"{what}: expected key=value, got a malformed item")
        k, v = it.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("seal")
    ap.add_argument("--out-dir")
    ap.add_argument("--analysis", default="auto", choices=["auto", "out-coded", "out", "out-kaug", "out-coded-kaug"])
    ap.add_argument("--frozen-tree", default=os.environ.get("EXHIBITS_FROZEN_TREE", ""))
    ap.add_argument("--parts", default="fidelity,models,causes")
    ap.add_argument("--map", action="append", default=[], help="fault_type=Paper row")
    ap.add_argument("--label", action="append", default=[], help="option=Label (default T=A)")
    ap.add_argument("--no-observability", action="store_true", help="do not look the observability class up (fault_observability = unknown, not a degraded part); for tests")
    ap.add_argument("--smallest-effect-sides", default="both", choices=["both", "plus"])
    args = ap.parse_args(argv)
    args.map = parse_kv(args.map, "--map")
    OPTION_LABEL.update(parse_kv(args.label, "--label"))
    os.umask(0o077)
    t0 = time.time()
    seal = Path(args.seal)
    out = Path(args.out_dir) if args.out_dir else seal / "exhibits"
    frozen = Path(args.frozen_tree) if args.frozen_tree else None
    if not seal.is_dir():
        print(f"exhibits: the seal is not a directory: {seal.name}")
        return RC_FAILED
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(out, 0o700)
    parts = [p.strip() for p in args.parts.split(",") if p.strip()]
    meta: dict = {"seal": seal.name, "out_dir": str(out), "parts": {}, "frozen_tree": str(frozen) if frozen else None}
    try:
        analysis, why = pick_analysis(seal, args.analysis)
        stamp = stamp_of(analysis, seal)
        meta["analysis_used"] = analysis.name
        if why:
            meta["analysis_note"] = why
            print(f"exhibits analysis: {why}")
        meta["stamp"] = stamp
    except ExhibitError as e:
        print(f"exhibits: {e}")
        return RC_FAILED
    cfg = frozen_config(frozen)
    meta["config"] = cfg
    obs = None if args.no_observability else observability_lookup(frozen)
    runners = {"fidelity": lambda: part_fidelity(seal, out, stamp, args, obs),
               "models": lambda: part_models(analysis, out, stamp, args),
               "causes": lambda: part_causes(seal, analysis, out, stamp, args, cfg)}
    for p in parts:
        if p not in runners:
            meta["parts"][p] = {"status": "failed", "note": "unknown part"}
            continue
        s0 = time.time()
        try:
            res = runners[p]()
        except FileExistsError as e:
            res = {"status": "refused", "note": safe_failure(e), "seconds": round(time.time() - s0, 2)}
        except Exception as e:    # a part never holds up the others
            res = {"status": "failed", "note": safe_failure(e), "seconds": round(time.time() - s0, 2)}
        meta["parts"][p] = res
        extra = ""
        if p == "causes" and res.get("checks"):
            bad = [c for c in res["checks"] if c.get("ok") is False and not c.get("informational")]
            extra = " checks=ok" if not bad else " checks=mismatch:" + ",".join(c["name"] for c in bad)      # the cells that differ are in the meta
        print(f"exhibits {p} {res['status']} rows={res.get('rows', 0)} files={res.get('files', 0)} seconds={res.get('seconds', 0)}{extra}" + (f" | {res['note']}" if res.get("note") else ""))
    sts = [meta["parts"][p]["status"] for p in meta["parts"]]
    meta["seconds"] = round(time.time() - t0, 2)
    try:
        write_atomic(out / "exhibits.meta.json" if not (out / "exhibits.meta.json").exists() else out / f"exhibits.meta.{int(time.time())}.json", json.dumps(meta, indent=1, default=str))
    except Exception:
        pass
    if sts and all(s == "ok" for s in sts):
        return RC_OK
    if sts and all(s == "refused" for s in sts):
        return RC_REFUSED
    if not any(s in ("ok", "degraded") for s in sts):
        return RC_FAILED
    return RC_PARTIAL


if __name__ == "__main__":
    sys.exit(main())
