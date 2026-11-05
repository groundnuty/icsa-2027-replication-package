"""The registered strict reading, beside every outcome it changes (amendment 36(d)).

Amendment 36(c) made the mask parser read dims named `latitude` / `longitude` as `lat` / `lon`; the lenient reading is the verdict, so such a
run is finished and scored. 36(d): "the registered strict reading is reported beside every outcome it changes: finished share, correctness and
omission measures, per option x layout x model, with the count of masks read through the alias."

The strict reading is expressed as ROWS, never as a second implementation of a measure: `strict_rows` turns each run whose mask was read through
the alias into the run the scorer writes for a failed mask, and every table below is the table the analysis already builds, run on those rows.
"""
from __future__ import annotations

import dataclasses
from typing import Iterable

import pandas as pd

from icsa.analysis import adapter, secondary as S
from icsa.analysis.config import Config
from icsa.records import ScoredRow

KEY = ["option", "layout", "model"]
TABLES = ("finished_share", "correctness", "omission")      # the three tables, per option x layout x model; the files are `strict_beside_<name>`

# What `icsa.scoring.scorer.score_run` leaves None when `finished` is False (every field computed from a parsed mask or report, or defined only for a
# finished run). `end_to_end` is False there, and the rest of the row (the report's own verdict, the alias flag and the strict reason, tokens, wall
# time, the coverage the instrument attached, the label's reasons) is attached whatever `finished` is.
UNFINISHED_NONE = (
    "label", "label_raw",                                                      # the omission label is carried only for a finished run
    "self_report_complete", "disclosed",                                       # read from report.json of a finished run
    "correct", "complete_extent",                                              # need a scored mask / the extents of a finished run
    "event_precision", "event_recall", "event_f1", "false_alarm",              # event matching and the false alarm come from the mask
    "day_agreement", "cell_day_f1", "cell_day_iou",                            # cell-day measures of the mask
    "cf_computation_f1", "cf_omission_f1",                                     # counterfactual comparisons, finished runs only
    "n_agent_events", "merges", "splits", "events_inconsistent",               # event accounting from the mask and the report's events
    "land_cells_set", "land_cell_days_set", "extent_account",                  # mask land cells; the report's extent against the instrument's
)


def strict_rows(rows: Iterable[ScoredRow]) -> list[ScoredRow]:
    """The rows under the registered strict reading of the mask (amendment 36(d)).

    A row whose `mask_dim_alias` is True (the mask was read through the latitude/longitude alias, valid or not) becomes, by `dataclasses.replace`,
    the row `score_run` writes for a run whose mask failed. A row whose `mask_dim_alias` is False (strict names) or None (scored before
    amendment 36, which scored strictly) is returned as it is, the same object, so the result equals the input there.

    Fields set on an alias row, and why:
    - `finished=False`, `mask_valid=False`: the strict reading refuses the dims, and a run is finished only if both files parse (report-spec).
    - `mask_invalid_reason = row.mask_strict_invalid_reason or "mask_invalid"`: the row's own strict verdict (the parser records it: "mask_invalid" when
      the alias was used), and the registered code where an older record has none.
    - `invalid_reason = row.report_invalid_reason or <that mask reason>`: the scorer's order, report reason first, then the mask's, and only then
      `termination_<x>`, which a mask reason always precedes.
    - `label`, `label_raw`: the scorer carries the omission label only for a finished run.
    - `self_report_complete`, `disclosed`: read from the report only for a finished run, so a failed run is not disclosed and has no claim.
    - `correct`, `end_to_end`: `correct` is None for an unfinished run and `end_to_end` is `bool(finished and ...)`, so False.
    - `event_precision`, `event_recall`, `event_f1`, `false_alarm`, `day_agreement`, `cell_day_f1`, `cell_day_iou`, `cf_computation_f1`,
      `cf_omission_f1`, `n_agent_events`, `merges`, `splits`, `events_inconsistent`, `land_cells_set`, `land_cell_days_set`, `complete_extent`,
      `extent_account`: each is computed from the scored mask (or the extent comparison) inside `if finished`, so None.
    - `label_after_inspection`, `coder_pair`: a run unfinished under the strict reading is never inspected (inspection refuses a label for it), so
      what inspection added is taken off. If the point coverage came from the coders (`coverage_source == "inspection"`), `coverage_baseline`,
      `coverage_target` and `coverage_source` go with it; the instrument's own coverage stays, as the scorer attaches it to unfinished runs too.
    Everything else is kept, as the scorer keeps it for a failed mask: `termination`, `report_valid`, `report_invalid_reason`, the alias flag and the
    strict reason, tokens, wall time, bytes, the coverage bounds, `label_reasons`, `n_ref_events`.

    Apply it AFTER `inspection.apply`, to the rows the tables are built from. Before it, `inspection.apply` refuses the coders' label for such a run
    ("not finished, so it has no label for inspection to resolve"); the order is not supported otherwise. Idempotent."""
    return [_strict(r) for r in rows]


def _strict(r: ScoredRow) -> ScoredRow:
    if r.mask_dim_alias is not True:
        return r
    mask_reason = r.mask_strict_invalid_reason or "mask_invalid"
    change = {f: None for f in UNFINISHED_NONE}
    change.update(finished=False, mask_valid=False, mask_invalid_reason=mask_reason, invalid_reason=r.report_invalid_reason or mask_reason,
                  end_to_end=False, label_after_inspection=None, coder_pair=None)
    if r.coverage_source == "inspection":
        change.update(coverage_baseline=None, coverage_target=None, coverage_source=None)
    return dataclasses.replace(r, **change)


# ------------------------------------------------------------------------------------------------------ the three tables
POOLED = "pooled"       # the `model` of a line over all of an option x layout's runs, as `secondary.pooled_model_sensitivity` names it


def _order(t: pd.DataFrame) -> pd.DataFrame:
    """Option, layout, then the models in order and the pooled line last of its cell."""
    return (t.assign(_pooled=t["model"] == POOLED).sort_values(["option", "layout", "_pooled", "model"], kind="stable")
            .drop(columns="_pooled").reset_index(drop=True))


def _finished_share(d: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    fin = d[d.finished.astype(bool) & ~d.time_cap.astype(bool)]
    t = pd.DataFrame({"N": d.groupby(by, sort=True).size(), "finished": fin.groupby(by, sort=True).size()}).fillna(0).astype({"finished": int}).reset_index()
    t["finished_share"] = t["finished"] / t["N"]
    return t


def _correctness(d: pd.DataFrame, by: list[str], omission: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(by, sort=True)
    t = pd.DataFrame({"N": g.size(), "event_f1_n": g["event_f1"].count(), "event_f1_mean": g["event_f1"].mean(),
                      "false_alarm_n": g["false_alarm"].count(), "false_alarm_rate": g["false_alarm"].mean()}).reset_index()
    return t.merge(omission[[*by, "end_to_end", "end_to_end_rate"]], on=by, how="left")


def _with_pooled_model(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t.insert(2, "model", POOLED)
    return t


def cell_tables(df: pd.DataFrame, cfg: Config) -> dict[str, pd.DataFrame]:
    """The three cell tables of a frame (`adapter.rows_to_frame`), one line per option x layout x model and, last in each option x layout, one line
    pooled over its models (`model` = "pooled"), over the options `denominator_table` counts (the main options and the pagination option).
    Descriptive, over regions, instances and seeds, like `denominators`; the inferential versions are the contrast tables.

    The pooled line is the same code on all the cell's runs, never an average of the models' lines (a rate is recomputed from the pooled counts, and
    a mean over the pooled runs weighs each run once); its counts are the models' sums.

    - `finished_share`: `N` the runs of the cell, `finished` the finished runs that were not time-capped, `finished_share` = finished / N.
      `N` is `denominator_table`'s `N`: `groupby(...).size()` over the frame's runs of those options, whatever their outcome (finished, time-capped
      or not), exhausted runs not being rows. `finished` is its `fin` (`finished` and not `time_cap`), so it equals O + C + U of the omission table.
    - `correctness`, the registered outcomes only: `event_f1_mean` over `event_f1_n` runs (the frame's `event_f1`: finished, not event-free, a value on
      record), `false_alarm_rate` over `false_alarm_n` runs (finished, event-free), and `end_to_end` / `end_to_end_rate` over all `N`, both taken from
      the omission table. A rate with no run is NaN, never 0.
    - `omission`: `secondary.denominator_table` unchanged (O, C, U, K, O', U', `unfinished_other`, the end-to-end counts, `omission_rate` and its
      bounds, `undisclosed_*`, `end_to_end_rate*`, `time_cap_share`): called on each model's runs and concatenated under a `model` column, and on all
      of them for the pooled line, which it already gives per option x layout. No omission formula is written here."""
    d = df[df.option.isin(cfg.options + [cfg["pagination"]["option"]])]
    if (d["model"] == POOLED).any():
        raise ValueError(f"a model named {POOLED!r} would be read as the pooled line")
    if d.empty:
        om_cols = [*S.denominator_table(d, cfg).columns.drop(["option", "layout"], errors="ignore")]
        return {"finished_share": pd.DataFrame(columns=[*KEY, "N", "finished", "finished_share"]),
                "correctness": pd.DataFrame(columns=[*KEY, "N", "event_f1_n", "event_f1_mean", "false_alarm_n", "false_alarm_rate", "end_to_end", "end_to_end_rate"]),
                "omission": pd.DataFrame(columns=[*KEY, *om_cols])}
    parts = []
    for model, g in d.groupby("model", sort=True):
        t = S.denominator_table(g, cfg)
        t.insert(2, "model", model)
        parts.append(t)
    omission = pd.concat([*parts, _with_pooled_model(S.denominator_table(d, cfg))], ignore_index=True)
    cell = ["option", "layout"]
    finished_share = pd.concat([_finished_share(d, KEY), _with_pooled_model(_finished_share(d, cell))], ignore_index=True)
    pooled_om = omission[omission["model"] == POOLED].drop(columns="model")
    correctness = pd.concat([_correctness(d, KEY, omission[omission["model"] != POOLED]),
                             _with_pooled_model(_correctness(d, cell, pooled_om))], ignore_index=True)
    return {"finished_share": _order(finished_share), "correctness": _order(correctness), "omission": _order(omission)}


def alias_counts(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Per option x layout x model, and pooled per option x layout, `n_alias`: the cell's runs whose mask was read through the alias
    (`mask_dim_alias` True; None and False are not). The pooled line is the cell's total."""
    d = df[df.option.isin(cfg.options + [cfg["pagination"]["option"]])]
    if d.empty:
        return pd.DataFrame(columns=[*KEY, "n_alias"])
    a = d["mask_dim_alias"].eq(True)
    per_model = a.groupby([d[k] for k in KEY], sort=True).sum().astype(int).rename("n_alias").reset_index()
    pooled = _with_pooled_model(a.groupby([d["option"], d["layout"]], sort=True).sum().astype(int).rename("n_alias").reset_index())
    return _order(pd.concat([per_model, pooled], ignore_index=True))


def beside(main: pd.DataFrame, strict_t: pd.DataFrame, n_alias: pd.DataFrame, name: str = "table") -> pd.DataFrame:
    """A cell table beside its strict twin, joined on (option, layout, model): `N` and `n_alias` once, then every measure column followed by its
    `_strict` column. The two must name the same cells and the same `N` (the strict reading changes outcomes, never which runs there are); anything
    else is an error, so a cell cannot go missing from one side unseen."""
    j = main.merge(strict_t, on=KEY, how="outer", suffixes=("", "_strict"), indicator=True)
    if (j["_merge"] != "both").any():
        raise ValueError(f"{name}: the main and the strict table do not name the same cells: "
                         f"{j.loc[j['_merge'] != 'both', KEY].values.tolist()}")
    if not (j["N"] == j["N_strict"]).all():
        raise ValueError(f"{name}: the strict reading changed the number of runs in a cell")
    measures = [c for c in main.columns if c not in (*KEY, "N")]
    j = j.merge(n_alias, on=KEY, how="left")
    j["n_alias"] = j["n_alias"].fillna(0).astype(int)
    return _order(j[[*KEY, "N", "n_alias"] + [c for m in measures for c in (m, f"{m}_strict")]])


def strict_beside(rows: Iterable[ScoredRow], cfg: Config, df: pd.DataFrame | None = None,
                  blocks: Iterable[str] | None = None) -> dict[str, pd.DataFrame]:
    """For each of `TABLES`: the main cell table and the same table on `strict_rows(rows)`, side by side (`beside`), with `n_alias`.

    `rows` are the scored rows the main tables are built from, after inspection (`strict_rows` goes after it). `df` is their frame if the caller has
    it (`adapter.rows_to_frame(rows, cfg, blocks)`); it is checked against the rows, never trusted. The strict frame goes through the same
    `rows_to_frame` selection (`blocks`, default the primary blocks; flagged and out-of-cohort runs left out), so both sides are over the same runs."""
    rows = list(rows)
    blocks = None if blocks is None else list(blocks)
    strict_df = adapter.rows_to_frame(strict_rows(rows), cfg, blocks)
    main_df = adapter.rows_to_frame(rows, cfg, blocks) if df is None else df
    if set(main_df["run_key"]) != set(strict_df["run_key"]) or len(main_df) != len(strict_df):
        raise ValueError("strict_beside: the frame given is not the frame of the rows given")
    main_t, strict_t, n_alias = cell_tables(main_df, cfg), cell_tables(strict_df, cfg), alias_counts(main_df, cfg)
    return {name: beside(main_t[name], strict_t[name], n_alias, name) for name in TABLES}
