"""Exhibits: option x layout figure with intervals, cause breakdown, cost table,
fault-injection fidelity sub-table (#14). Tables are CSV + Markdown."""
from __future__ import annotations

import dataclasses

import pathlib

import matplotlib
import numpy as np
import pandas as pd

from icsa.analysis import adapter, config as cfgmod, contrasts as C
from icsa.analysis.config import Config
from icsa.scoring.scorer import invalid_rates

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def to_markdown(df: pd.DataFrame) -> str:
    if not len(df):
        return "(empty)\n"
    fmt = lambda v: f"{v:.4g}" if isinstance(v, (float, np.floating)) else str(v)
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(lines) + "\n"


def write_table(df: pd.DataFrame, out: pathlib.Path, name: str) -> None:
    df.to_csv(out / f"{name}.csv", index=False)
    (out / f"{name}.md").write_text(to_markdown(df))


def level_table(df: pd.DataFrame, cfg: Config, outcome: str, rng: np.random.Generator | None = None,
                B: int | None = None) -> pd.DataFrame:
    """Region-level mean per option x layout with a cluster-bootstrap CI (regions resampled,
    equal weight over models)."""
    o = C.OUTCOME[outcome]
    bs = cfg["bootstrap"]
    rng = rng or np.random.default_rng(bs["seed"])
    inst = C.instance_values(df[df.option.isin(cfg.options)], o.column)
    rows = []
    for (opt, layout), g in inst.groupby(["option", "layout"], sort=True):
        rm = g.groupby(["region_id", "model"], as_index=False)["value"].mean().rename(columns={"value": "diff"})
        mat, regions, _ = C._matrix(rm)
        (pt, lo, hi), _ = C.cluster_bootstrap(mat, int(B or bs["B"]), float(bs["ci_level"]), rng)
        rows.append({"outcome": outcome, "option": opt, "layout": layout, "n_regions": len(regions),
                     "mean": pt, "ci_lo": lo, "ci_hi": hi})
    # the columns stay when no region has the outcome (every run time-capped, say): a valid population, not bad input (b3 #5)
    return pd.DataFrame(rows, columns=["outcome", "option", "layout", "n_regions", "mean", "ci_lo", "ci_hi"])


LEVEL_OUTCOMES = ["omission", "coverage_baseline", "coverage_target", "event_f1"]   # the figure's panels


def outcome_figure(levels: pd.DataFrame, cfg: Config, path: pathlib.Path) -> None:
    outs = LEVEL_OUTCOMES
    fig, axes = plt.subplots(1, len(outs), figsize=(4 * len(outs), 3.4), sharey=False)
    colors = {"S1": "#1f77b4", "S2": "#d95f02"}
    for ax, name in zip(axes, outs):
        t = levels[levels.outcome == name]
        for j, layout in enumerate(cfg.layouts):
            s = t[t.layout == layout].set_index("option").reindex(cfg.options)
            x = np.arange(len(cfg.options)) + (j - 0.5) * 0.25
            ax.errorbar(x, s["mean"], yerr=[s["mean"] - s["ci_lo"], s["ci_hi"] - s["mean"]], fmt="o", capsize=3,
                        color=colors.get(layout, None), label=layout)
        ax.set_xticks(range(len(cfg.options)), cfg.options)
        ax.set_title(name.replace("_", " "))
        ax.set_ylim(0, 1)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("region-level mean (95% cluster-bootstrap CI)")
    axes[-1].legend(title="layout", frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

POP_INCORRECT = "incorrect_complete"      # icsa.causes: finished, complete, wrong


def cause_breakdown(df: pd.DataFrame, cfg: Config, causes: pd.DataFrame | None = None) -> pd.DataFrame:
    """Counts of run outcomes per option x layout.

    Classes: not finished (by termination), finished-omitting (disclosed or
    silent), finished-complete, finished-unknown. If `causes` (columns block, run_key,
    cause) is given, coded causes of the analysed blocks are appended as further rows.
    """
    d = df[df.option.isin(cfg.options + [cfg["pagination"]["option"]])].copy()

    def cls(r):
        if not r.finished:
            return f"unfinished:{r.termination}"
        if r.label == "omitting":
            return "omitting:disclosed" if r.disclosed == 1.0 else "omitting:silent"
        return f"finished:{r.label}"

    d["class"] = d.apply(cls, axis=1)
    t = d.groupby(["option", "layout", "class"]).size().rename("n").reset_index()
    t["share"] = t["n"] / t.groupby(["option", "layout"])["n"].transform("sum")
    if causes is not None and len(causes):
        # run_key carries no block: a pilot run and the main run of the same cell share it. A cause is
        # therefore joined on (block, run_key), so a coded pilot run can never attach to a main run.
        if "block" not in causes.columns:
            raise ValueError("causes: a block column is required (run_key alone cannot tell a pilot run from "
                             "the main run of the same cell)")
        causes = causes[causes["block"].isin(cfg["blocks"]["primary"])]
        if causes.duplicated(["block", "run_key"]).any():
            raise ValueError("causes: duplicate (block, run_key); list each analysed run once")
        if len(causes) and not len(causes.merge(df[["block", "run_key"]], on=["block", "run_key"])):
            raise ValueError("causes: no (block, run_key) matches an analysed run (key format?)")
        extra = [c for c in ("cause_detail", "population") if c in causes.columns]
        j = d.merge(causes[["block", "run_key", "cause", *extra]], on=["block", "run_key"])
        # incorrect_complete (finished, complete, wrong) is its own breakdown, never merged with omission causes
        inc = (j["population"] == POP_INCORRECT) if "population" in j.columns else pd.Series(False, index=j.index)

        def count(x: pd.DataFrame, col: str, prefix: str) -> pd.DataFrame:
            c = x.groupby(["option", "layout", col]).size().rename("n").reset_index().rename(columns={col: "class"})
            c["class"] = prefix + c["class"].astype(str)
            c["share"] = np.nan
            return c
        parts = [count(j[~inc], "cause", "cause:")]               # totals per bare cause, as before
        if "cause_detail" in j.columns:                          # the split (e.g. truncated_listing:client|agent)
            sub = j[~inc & (j["cause_detail"].astype(str) != j["cause"].astype(str))]
            if len(sub):
                parts.append(count(sub, "cause_detail", "cause_detail:"))
        if inc.any():
            parts.append(count(j[inc], "cause", "incorrect_complete:"))
        t = pd.concat([t, *parts], ignore_index=True)
    return t


def recovered_truncated_listing(df: pd.DataFrame, cfg: Config, flags: pd.DataFrame | None) -> pd.DataFrame:
    """Per option: the rate of runs that recovered from a truncated listing (#17 ruling), over ALL analysed runs.

    `flags` is #17's `flags_table()` / `<out>.flags.csv` (block, run_key, option, recovered_from_truncated_listing,
    listing_evidence_incomplete), one line for every run it coded or skipped. Only runs of the analysed set are
    counted; a run with no value is `unknown`, never False, and a run absent from the table is `no_flag`. The rate is
    recovered / (recovered + not recovered). `listing_evidence_incomplete` is counted per option beside it.
    An empty table without the input."""
    cols = ["option", "runs", "with_flag_line", "recovered", "not_recovered", "unknown", "no_flag", "recovered_rate",
            "listing_evidence_incomplete"]
    if flags is None or not len(flags):
        return pd.DataFrame(columns=cols)
    need = {"block", "run_key", "recovered_from_truncated_listing", "listing_evidence_incomplete"}
    if need - set(flags.columns):
        raise ValueError(f"cause flags: columns {sorted(need - set(flags.columns))} are missing")
    if flags.duplicated(["block", "run_key"]).any():
        raise ValueError("cause flags: duplicate (block, run_key); list each run once")
    j = df[["block", "run_key", "option"]].merge(flags[["block", "run_key", "recovered_from_truncated_listing",
                                                       "listing_evidence_incomplete"]], on=["block", "run_key"], how="left",
                                                 indicator=True)
    if not (j["_merge"] == "both").any():
        raise ValueError("cause flags: no (block, run_key) matches an analysed run (key format?)")

    def known(x):
        return x is not None and x is not pd.NA and not (isinstance(x, float) and np.isnan(x))
    rows = []
    for opt, g in j.groupby("option", sort=True):
        line = g["_merge"] == "both"
        v = g.loc[line, "recovered_from_truncated_listing"]
        k = v.map(known)
        yes = int(sum(bool(x) for x in v[k]))
        inc = g.loc[line, "listing_evidence_incomplete"].map(lambda x: known(x) and bool(x))
        rows.append({"option": opt, "runs": len(g), "with_flag_line": int(line.sum()), "recovered": yes,
                     "not_recovered": int(k.sum()) - yes, "unknown": int((~k).sum()), "no_flag": int((~line).sum()),
                     "recovered_rate": yes / int(k.sum()) if k.sum() else np.nan,
                     "listing_evidence_incomplete": int(inc.sum())})
    return pd.DataFrame(rows, columns=cols)


def cause_figure(t: pd.DataFrame, path: pathlib.Path) -> None:
    t = t[~t["class"].str.startswith(("cause:", "cause_detail:", "incorrect_complete:"))]
    piv = t.pivot_table(index=["option", "layout"], columns="class", values="share", fill_value=0.0)
    ax = piv.plot(kind="bar", stacked=True, figsize=(9, 4), width=0.8, colormap="tab20")
    ax.set_ylabel("share of runs")
    ax.legend(fontsize=7, frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left")
    ax.figure.tight_layout()
    ax.figure.savefig(path, dpi=150)
    plt.close(ax.figure)


def out_of_cohort_table(rows, cfg: Config) -> pd.DataFrame:
    """The runs of the primary blocks that started at or after the cohort cut (science, #2, 2 Nov 11:54Z): kept, and reported descriptively, one line per run. They are
    in no contrast: `adapter.exclusion_reason` leaves them out."""
    late = [dataclasses.replace(r, out_of_cohort=False) for r in rows if r.out_of_cohort and not r.exclude_from_analysis]
    if not late:
        return pd.DataFrame(columns=["run_key", "option", "layout", "model"])
    return adapter.rows_to_frame(late, cfg)


def bytes_unknown_table(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Per option x model: runs whose bytes between sites are not known (science, 2 Nov: counted, left out of the mean, no retry)."""
    d = df[df.option.isin(cfg.options + [cfg["pagination"]["option"]])]
    g = d.groupby(["option", "model"], sort=True)["bytes_between_sites"]
    return pd.DataFrame({"runs": g.size(), "bytes_unknown": g.apply(lambda s: int(s.isna().sum()))}).reset_index()


def invalid_rates_table(rows, cfg: Config) -> pd.DataFrame:
    """The report spec's "rate of each reason, per option", over the primary blocks' runs (`icsa.scoring.scorer.invalid_rates`):
    one line per option and measure. A run can appear under several reasons."""
    kept, _ = adapter.select_rows(rows, cfg)
    out = []
    for opt, r in invalid_rates(kept).items():
        for measure, rate in (("unfinished", r["unfinished_rate"]), ("report_invalid", r["report_invalid_rate"]),
                              ("mask_invalid", r["mask_invalid_rate"]),
                              *((f"reason:{k}", v) for k, v in sorted(r["reasons"].items()))):
            out.append({"option": opt.value, "runs": r["n"], "measure": measure, "rate": rate})
    return pd.DataFrame(out, columns=["option", "runs", "measure", "rate"])


def cost_table(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Per option x layout: mean and median tokens, wall time, bytes; ratios to the
    cheapest option within the layout (region-level geometric means are in the
    tokens contrasts)."""
    d = df[df.option.isin(cfg.options + [cfg["pagination"]["option"]])]
    fields = list(cfg["outcomes"]["tokens_fields"])
    d = d.assign(_t=d[fields].sum(axis=1, skipna=False), _seen=d[[f + "_observed" for f in fields]].sum(axis=1))
    g = d.groupby(["option", "layout"], sort=True)
    t = pd.DataFrame({
        "runs": g.size(),
        "tokens_mean": g["_t"].mean(),                   # of the runs whose usage is complete: the count stands beside it
        "tokens_median": g["_t"].median(),
        "tokens_runs": g["_t"].count(),
        # beside the means: runs cut mid-request count at their completed tokens (science, #34); a cut in the FIRST request has none and is left out
        "usage_flagged_runs": g["usage_complete"].apply(lambda s: int(len(s) - s.astype(bool).sum())),
        "first_request_cuts": g["first_request_cut"].apply(lambda s: int(s.astype(bool).sum())),
        "tokens_observed_mean": g["_seen"].mean(),       # every run, as far as it was seen: not a cost
        "input_tokens_mean": g["input_tokens"].mean(),
        "output_tokens_mean": g["output_tokens"].mean(),
        "tokens_into_context_mean": g["tokens_into_context"].mean(),      # of the runs counted: see the count beside it
        "tokens_into_context_runs": g["tokens_into_context"].count(),
        "bytes_into_context_mean": g["bytes_into_context"].mean(),
        "bytes_between_sites_mean": g["bytes_between_sites"].mean(),      # of the runs whose bytes are known: NaN is left out, and never reads as 0
        "bytes_between_sites_unknown": g["bytes_between_sites"].apply(lambda s: int(s.isna().sum())),
        "wall_time_s_median": g["wall_time_s"].median(),
    }).reset_index()
    floor = t[t.option.isin(cfg.options)].groupby("layout")["tokens_mean"].min()
    t["tokens_ratio_to_min"] = t["tokens_mean"] / t["layout"].map(floor)
    return t


def usage_flagged_table(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Per option x layout x model, on the cost table's runs: the runs whose usage is flagged (`usage_complete` False: a request was abandoned or a reply
    carried no usage), their share, and the runs cut in their FIRST request (no completed request on record, so no tokens: the only flagged runs the tokens
    outcome leaves out). The others count in it at their completed requests' tokens (science, #34, 21:41Z and 21:45Z)."""
    d = df[df.option.isin(cfg.options + [cfg["pagination"]["option"]])]
    g = d.groupby(["option", "layout", "model"], sort=True)
    t = pd.DataFrame({"runs": g.size(),
                      "flagged_runs": g["usage_complete"].apply(lambda s: int(len(s) - s.astype(bool).sum())),
                      }).reset_index()
    t["flagged_share"] = t["flagged_runs"] / t["runs"]
    cuts = g["first_request_cut"].apply(lambda s: int(s.astype(bool).sum())).rename("first_request_cuts").reset_index()
    return t.merge(cuts, on=["option", "layout", "model"], how="left")


FIDELITY_FIELDS = ("fault_injected", "fault_detected", "record_type", "fault_type", "condition", "observability", "unit_fp")


def fault_injection_adapter(df_rows, cfg: Config | None = None) -> pd.DataFrame:
    """One row per (run, record) of #11's scripted runs, from their `platform_record`, with the dimensions H3 is registered
    on: option x layout x record x condition, and whether the fault was observable by design. Change here only.

    A record that carries a fault outcome and lacks any of the rest is an error, and so is a run with no scored outcome:
    pooled or read as clean, it would change H3's number without a sign (b3 #2). A record with no outcome at all is no
    fault-injection run, so a campaign row passes through this as nothing.

    These rows come from #11's scripted runs, which carry no campaign block of the primary
    allow-list, so the primary block filter does not apply. A row is left out when it is flagged
    `exclude_from_analysis` or sits in a campaign block of `[blocks].never` (pilot, calibration,
    optional_*): the 42-run calibration block never feeds this table. A row with no block is kept.
    """
    never = set((cfg or cfgmod.load())["blocks"]["never"])
    recs = []
    for r in df_rows:
        if r.exclude_from_analysis or r.block in never:
            continue
        pr = r.platform_record or {}
        if "fault_injected" not in pr and "fault_detected" not in pr:
            continue
        missing = [f for f in FIDELITY_FIELDS if f not in pr]
        if missing:
            raise ValueError(f"run {r.run.key()}: its platform_record lacks {missing}")
        if type(pr["fault_injected"]) is not bool or type(pr["fault_detected"]) is not bool:
            raise ValueError(f"run {r.run.key()}: fault_injected and fault_detected must be true or false, "
                             f"not {pr['fault_injected']!r} and {pr['fault_detected']!r}")
        recs.append({"option": r.run.option.value, "layout": r.run.layout.value, "record": pr["record_type"],
                     "condition": pr["condition"], "fault_type": pr["fault_type"],
                     "observable": pr["observability"] == "observable", "injected": pr["fault_injected"],
                     "detected": pr["fault_detected"], "false_flags": int(pr["unit_fp"] or 0) > 0})
    return pd.DataFrame(recs, columns=["option", "layout", "record", "condition", "fault_type", "observable", "injected",
                                       "detected", "false_flags"])


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return float(c - h), float(c + h)


FIDELITY_CELL = ["option", "layout", "record", "condition"]
FIDELITY_COLUMNS = [*FIDELITY_CELL, "subset", "tested", "n_faulted", "n_detected", "n_control", "n_false_alarm",
                    "n_false_flag_faulted", "n_true_and_false_flag", "n_false_flag_unobservable",
                    "recall", "recall_lo", "recall_hi", "precision", "precision_lo", "precision_hi",
                    "false_alarm", "false_alarm_lo", "false_alarm_hi"]


def fault_fidelity_table(fi: pd.DataFrame) -> pd.DataFrame:
    """Recall and precision per option x layout x record x condition, the cell H3 is registered on (`parameters.md`). Two rows
    per cell: subset `observable`, tested, over the faulted runs observable by design for that record; and subset `all`,
    reported only, over every faulted run. Fault-free runs are in both. As registered, recall = detected faulted runs /
    faulted runs and precision = true flags / all flags, fault-free runs included; a faulted run whose flags are all
    false is a false flag. A false flag on a run the tested subset drops stays out of its precision and is counted in
    `n_false_flag_unobservable`, as `icsa.faults.fidelity` has it.

    There is no verdict here. A cell's verdict needs its whole planned allocation, which these rows do not hold: it is
    `h3_table.csv`'s (`icsa.faults.fidelity.h3_table`), and `with_h3_verdicts` joins it on."""
    rows = []
    for cell, g in fi.groupby(FIDELITY_CELL, sort=True):
        ctrl = g[~g.injected.astype(bool)]
        fa = int(ctrl.detected.astype(bool).sum())
        for subset, tested in (("observable", True), ("all", False)):
            faulted = g[g.injected.astype(bool)]
            site_g = faulted[faulted.observable.astype(bool)] if tested else faulted
            dropped = faulted[~faulted.observable.astype(bool)] if tested else faulted.iloc[0:0]
            tp = int(site_g.detected.astype(bool).sum())
            ff = int((~site_g.detected.astype(bool) & site_g.false_flags.astype(bool)).sum())
            flagged = tp + ff + fa
            r_lo, r_hi = wilson(tp, len(site_g))
            p_lo, p_hi = wilson(tp, flagged)
            a_lo, a_hi = wilson(fa, len(ctrl))
            rows.append({**dict(zip(FIDELITY_CELL, cell)), "subset": subset, "tested": tested, "n_faulted": len(site_g),
                         "n_detected": tp, "n_control": len(ctrl), "n_false_alarm": fa, "n_false_flag_faulted": ff,
                         "n_true_and_false_flag": int((site_g.detected.astype(bool) & site_g.false_flags.astype(bool)).sum()),
                         "n_false_flag_unobservable": int(dropped.false_flags.astype(bool).sum()),
                         "recall": tp / len(site_g) if len(site_g) else np.nan, "recall_lo": r_lo, "recall_hi": r_hi,
                         "precision": tp / flagged if flagged else np.nan, "precision_lo": p_lo, "precision_hi": p_hi,
                         "false_alarm": fa / len(ctrl) if len(ctrl) else np.nan, "false_alarm_lo": a_lo, "false_alarm_hi": a_hi})
    return pd.DataFrame(rows, columns=FIDELITY_COLUMNS)


def fidelity_exhibit(fi: pd.DataFrame, h3: pd.DataFrame | None) -> tuple[pd.DataFrame, str]:
    """The table written, and what it is: `not_run` (no fault-injection run), `no_verdicts` (rows and no `h3_table.csv`), or
    `verdicts`. An empty table must never look like a result, so `not_run` is a row that says so."""
    table = fault_fidelity_table(fi)
    if table.empty:
        return pd.DataFrame([{"subset": "all", "tested": False, "status": "not_run"}], columns=[*FIDELITY_COLUMNS, "status", "meets_h3"]), "not_run"
    return (table, "no_verdicts") if h3 is None else (with_h3_verdicts(table, h3), "verdicts")


def with_h3_verdicts(table: pd.DataFrame, h3: pd.DataFrame) -> pd.DataFrame:
    """`fault_fidelity_table` with each cell's verdict from `h3_table.csv`, the one place that can give it. The two compute the
    same numbers from different inputs (these rows, and the runs), so they are compared here: any disagreement stops the
    analysis. Where `h3_table.csv` gives no number the rows can be compared with (a cell not testable or incomplete, whose
    metrics it leaves undefined), only the counts are, and its undefined metric stands. A cell of the plan with no scored
    run is in `h3_table.csv` only, and keeps its row with its counts, so it cannot vanish."""
    key = [*FIDELITY_CELL, "subset"]
    h = h3[h3["fault_type"] == "all"][[*key, "tested", "n_faulted", "n_control", "recall", "precision", "status", "meets_h3"]]
    m = table.merge(h, how="outer", on=key, suffixes=("", "_h3"), indicator=True)
    only_here = m[m["_merge"] == "left_only"]
    if len(only_here):
        raise ValueError(f"cells in the fidelity rows and not in h3_table.csv: {only_here[key].to_dict('records')[:3]}")
    only_h3 = m["_merge"] == "right_only"
    if ((m.loc[only_h3, "n_faulted_h3"].fillna(0) > 0) | (m.loc[only_h3, "n_control_h3"].fillna(0) > 0)).any():
        raise ValueError(f"cells with scored runs in h3_table.csv and none in the fidelity rows: {m.loc[only_h3, key].to_dict('records')[:3]}")
    both = m["_merge"] == "both"
    judged = both & m["status"].isin(["pass", "fail", "reported"])
    for col, where in (("n_faulted", both), ("n_control", both), ("recall", judged), ("precision", judged)):
        a, b = m.loc[where, col].astype(float), m.loc[where, col + "_h3"].astype(float)
        differ = (a.isna() != b.isna()) | ((a - b).abs() > 1e-9)
        if differ.any():
            raise ValueError(f"the fidelity rows and h3_table.csv disagree on {col}: {m.loc[differ[differ].index, key].to_dict('records')[:3]}")
    m.loc[~judged, "recall"] = m.loc[~judged, "recall_h3"]
    m.loc[~judged, "precision"] = m.loc[~judged, "precision_h3"]
    m["tested"] = m["tested"].astype(object).where(~only_h3, m["tested_h3"])
    for col in ("n_faulted", "n_control"):
        m.loc[only_h3, col] = m.loc[only_h3, col + "_h3"]
    return m[[*FIDELITY_COLUMNS, "status", "meets_h3"]].sort_values(key, ignore_index=True)
