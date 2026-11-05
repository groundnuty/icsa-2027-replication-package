"""Infrastructure failures in the analysis (#14; protocol/parameters.md, "Infrastructure failures").

A run whose three infrastructure attempts are used up (*exhausted*) has no outcomes, so no scored
row, and would vanish. The campaign store's export (`icsa.campaign.export`, format
`icsa-infra-export-v1`) lists them; `run_all` REQUIRES it (an explicitly empty account is fine, a
missing one is an error). The rules:

- exhausted runs are not in any primary denominator (they are not rows);
- they are reported per cell (block x option x layout x model) and per option;
- the sensitivity row adds those of the primary scope as time-capped (K) to the omission bounds and
  as failures (0) to the end-to-end outcome (`exhausted_frame`, used by `secondary.exhausted_sensitivity`);
- per-run outcomes are those of the first attempt without an infrastructure failure: a scored row
  of any other attempt (`ScoredRow.infra_failure`, or an `attempt` that is not the analysed one in the
  export) is an error;
- discarded attempts' tokens and time are reported per option.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
from typing import Iterable

import pandas as pd

from icsa.analysis import adapter
from icsa.analysis.config import Config
from icsa.campaign.export import (ANALYSED_FIELDS, EXHAUSTED_FIELDS, FORMAT, UNFINISHED_FIELDS,
                                  USAGE_FIELDS)
from icsa.records import ScoredRow

EXHAUSTED_TERMINATION = "infra_exhausted"


@dataclasses.dataclass(frozen=True)
class InfraAccount:
    exhausted: tuple[dict, ...] = ()
    unfinished: tuple[dict, ...] = ()
    discarded: tuple[dict, ...] = ()
    analysed: tuple[dict, ...] = ()
    sha256: str | None = None

    @classmethod
    def empty(cls) -> "InfraAccount":
        """The explicit statement that no run is exhausted and no attempt was discarded."""
        return cls()


def parse_export(d: dict, sha: str | None = None) -> InfraAccount:
    if not isinstance(d, dict) or d.get("format") != FORMAT:
        raise ValueError(f"infra export: format must be {FORMAT!r}")
    out = {}
    for key, fields in (("exhausted_runs", EXHAUSTED_FIELDS), ("unfinished_runs", UNFINISHED_FIELDS),
                        ("discarded_usage", USAGE_FIELDS), ("analysed_attempts", ANALYSED_FIELDS)):
        if key not in d or not isinstance(d[key], list):
            raise ValueError(f"infra export: list {key!r} is missing (write an empty list if there are none)")
        for e in d[key]:
            miss = [f for f in fields if f not in e]
            if miss:
                raise ValueError(f"infra export: {key} entry {e.get('run_key', e)} lacks {miss}")
        out[key] = tuple(d[key])
    return InfraAccount(out["exhausted_runs"], out["unfinished_runs"], out["discarded_usage"],
                        out["analysed_attempts"], sha)


def load_export(path: str | pathlib.Path) -> InfraAccount:
    raw = pathlib.Path(path).read_bytes()
    return parse_export(json.loads(raw), hashlib.sha256(raw).hexdigest())


def coerce(infra) -> InfraAccount:
    if infra is None:
        raise ValueError("the infrastructure-failure account is required: pass the campaign export "
                         "(icsa.campaign export-infra) or InfraAccount.empty() to state that there is none")
    if isinstance(infra, InfraAccount):
        return infra
    if isinstance(infra, (str, pathlib.Path)):
        return load_export(infra)
    raise TypeError(f"infra must be an InfraAccount or a path, not {type(infra).__name__}")


def _why_out(block: str, flagged: bool, allowed: set[str]) -> str | None:
    if flagged:
        return "flagged"
    return None if block in allowed else "block"


def check_against_rows(acc: InfraAccount, rows: Iterable[ScoredRow]) -> None:
    """Contradictions between the account and the scored rows are errors, not silent choices."""
    rows = list(rows)
    for r in rows:
        if r.infra_failure:
            raise ValueError(f"run {r.run.key()} (block {r.block}): the row scores a discarded attempt "
                             f"(attempt {r.attempt}, infra_failure); the analysed attempt is the first without one")
    scored = {(r.block, r.run.key()): r for r in rows}
    for u in acc.unfinished:
        if (u["block"], u["key"]) in scored:
            raise ValueError(f"run {u['run_key']} is {u['status']} in the export but also scored: no analysed attempt exists")
    for e in acc.exhausted:
        if (e["block"], e["key"]) in scored:
            raise ValueError(f"run {e['run_key']} is exhausted in the export but also scored: it has outcomes or not")
    if acc.analysed or acc.exhausted or acc.unfinished or acc.discarded:
        # a real campaign export (only InfraAccount.empty() is exempt): every scored run must be one of its analysed runs
        known = {(a["block"], a["key"]) for a in acc.analysed}
        extra = [k for k in scored if k[0] is not None and k not in known]
        if extra:
            raise ValueError(f"{len(extra)} scored run(s) are not done in the campaign export, e.g. {extra[0]}")
    missing = [a["run_key"] for a in acc.analysed if (a["block"], a["key"]) not in scored]
    if missing:
        raise ValueError(f"{len(missing)} run(s) are done in the campaign but have no scored row, e.g. {missing[0]}: "
                         "score every done run (an invalid one gets a not-finished row) so none vanishes")
    for a in acc.analysed:
        r = scored[(a["block"], a["key"])]
        if r.attempt != a["attempt"]:
            raise ValueError(f"run {a['run_key']}: the row scores attempt {r.attempt}, the analysed one is {a['attempt']}")


def exhausted_scope(acc: InfraAccount, cfg: Config) -> tuple[list[dict], pd.DataFrame]:
    """The exhausted runs of the primary scope (same rule as `adapter.exclusion_reason`) and an
    account with one line per (block, status), status in exhausted_kept | exhausted_flagged | exhausted_block."""
    allowed = set(cfg["blocks"]["primary"])
    kept, count = [], {}
    for e in acc.exhausted:
        why = _why_out(e["block"], bool(e["exclude_from_analysis"]), allowed)
        k = (e["block"], "exhausted_" + ("kept" if why is None else why))
        count[k] = count.get(k, 0) + 1
        if why is None:
            kept.append(e)
    return kept, pd.DataFrame([{"block": b, "status": s, "n": n} for (b, s), n in sorted(count.items())],
                              columns=["block", "status", "n"])


def exhausted_frame(kept: list[dict]) -> pd.DataFrame:
    """Sensitivity rows: time-capped (K) in the omission bounds, failures in the end-to-end outcome,
    undefined everywhere else (K is out of the undisclosed-omission rate)."""
    nan = float("nan")
    recs = [{
        "run_key": e["key"], "block": e["block"], "instance_id": e["instance_id"], "region_id": e["region_id"],
        "option": e["option"], "layout": e["layout"], "model": e["model"], "seed": e["seed"],
        "event_free": False, "termination": EXHAUSTED_TERMINATION, "finished": False, "label": None,
        "time_cap": True, "unknown": False, "omit": nan, "omit_lower": 0.0, "omit_upper": 1.0,
        "undis": nan, "undis_lower": nan, "undis_upper": nan, "end_to_end_upper": 0.0,
        "in_bounds_denominator": True, "disclosed": nan, "coverage_baseline": nan, "coverage_target": nan,
        "coverage_baseline_lower": nan, "coverage_target_lower": nan, "coverage_baseline_upper": nan, "coverage_target_upper": nan,
        "event_f1": nan, "false_alarm": nan, "end_to_end": 0.0, "log2_tokens": nan, "input_tokens": nan, "input_tokens_observed": nan,
        "output_tokens": nan, "output_tokens_observed": nan, "wall_time_s": nan, "bytes_between_sites": nan, "bytes_into_context": 0,
        "tokens_into_context": nan, "backend": "unknown",
        "label_instrument": None, "instrument_unknown": False, "label_source": None, "raw_omitting_unknown_not_by_rule": False,
        "coder_pair": None} for e in kept]
    return pd.DataFrame.from_records(recs, columns=adapter.COLUMNS)


def exhausted_per_cell(acc: InfraAccount, df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Per cell (block x option x layout x model): exhausted runs, how many of them the primary scope uses
    the block, and the scored runs of the primary frame in the cell (primary blocks only).
    `n_exhausted_in_primary_scope` counts those that enter the sensitivity row (primary block, not flagged). Of the exhausted runs, `n_no_outcome_at_snapshot` are
    cohort runs with no outcome at the paper's snapshot, counted as exhausted by amendment 29(c), and `n_infrastructure` used up their attempts."""
    allowed = set(cfg["blocks"]["primary"])
    cols = ["block", "option", "layout", "model"]
    ex = pd.DataFrame([{**{c: e[c] for c in cols},
                        "in_scope": _why_out(e["block"], bool(e["exclude_from_analysis"]), allowed) is None,
                        "converted": bool(e["no_outcome_at_snapshot"])}
                       for e in acc.exhausted], columns=cols + ["in_scope", "converted"])
    n = ex.groupby(cols, sort=True).agg(n_exhausted=("in_scope", "size"), n_exhausted_in_primary_scope=("in_scope", "sum"),
                                        n_no_outcome_at_snapshot=("converted", "sum")).reset_index()
    n["n_exhausted_in_primary_scope"] = n["n_exhausted_in_primary_scope"].astype(int)
    n["n_no_outcome_at_snapshot"] = n["n_no_outcome_at_snapshot"].astype(int)
    n.insert(n.columns.get_loc("n_no_outcome_at_snapshot"), "n_infrastructure", n["n_exhausted"] - n["n_no_outcome_at_snapshot"])
    sc = df.groupby(cols, sort=True).size().rename("n_scored").reset_index()
    t = n.merge(sc, on=cols, how="left")
    t["n_scored"] = t["n_scored"].fillna(0).astype(int)
    return t


def infra_per_option(acc: InfraAccount, cfg: Config) -> pd.DataFrame:
    """Per option, primary blocks: runs whose analysed attempt exists, exhausted runs, discarded
    attempts and their tokens and time (interrupted and harness-error attempts separately). 'attempts' counts the
    analysed attempts plus the discarded ones."""
    allowed = set(cfg["blocks"]["primary"])
    rows: dict[str, dict] = {}

    def row(o: str) -> dict:
        return rows.setdefault(o, dict(option=o, runs_with_outcome=0, runs_exhausted=0, discarded_attempts=0,
                                       discarded_input_tokens=0, discarded_output_tokens=0, discarded_wall_s=0.0,
                                       interrupted_attempts=0, interrupted_input_tokens=0,
                                       interrupted_output_tokens=0, interrupted_wall_s=0.0,
                                       harness_error_attempts=0, harness_error_input_tokens=0,
                                       harness_error_output_tokens=0, harness_error_wall_s=0.0))
    for a in acc.analysed:
        if a["block"] in allowed:
            row(a["option"])["runs_with_outcome"] += 1
    for e in acc.exhausted:
        if e["block"] in allowed and not e["exclude_from_analysis"]:
            row(e["option"])["runs_exhausted"] += 1
    for u in acc.discarded:
        if u["block"] in allowed:
            r = row(u["option"])
            r["discarded_attempts"] += u["attempts"]
            r["discarded_input_tokens"] += u["input_tokens"]
            r["discarded_output_tokens"] += u["output_tokens"]
            r["discarded_wall_s"] += u["wall_s"]
            for k in ("attempts", "input_tokens", "output_tokens", "wall_s"):
                r["interrupted_" + k] += u["interrupted_" + k]
                r["harness_error_" + k] += u["harness_error_" + k]     # attempts lost to a bug of ours (re-queued): billed, never analysed
    t = pd.DataFrame(sorted(rows.values(), key=lambda r: r["option"]), columns=[
        "option", "runs_with_outcome", "runs_exhausted", "discarded_attempts", "discarded_input_tokens",
        "discarded_output_tokens", "discarded_wall_s", "interrupted_attempts", "interrupted_input_tokens",
        "interrupted_output_tokens", "interrupted_wall_s", "harness_error_attempts", "harness_error_input_tokens",
        "harness_error_output_tokens", "harness_error_wall_s"])
    t.insert(3, "attempts", t["runs_with_outcome"] + t["discarded_attempts"])
    return t


def unfinished_per_cell(acc: InfraAccount, cfg: Config) -> pd.DataFrame:
    """Per cell of the primary scope: the runs with no outcome when the analysis starts, reported as not finished (amendment 29(c), for a descriptive part). They are
    no rows, so they enter no denominator, bound, contrast or sensitivity row. At the paper's fixed snapshot the cut turns them into exhausted runs first
    (`snapshot --no-outcome as-exhausted`), so none is left here, and `exhausted_per_cell` counts them apart. `n_not_finished_in_cohort`: started, or deferred
    by a cap, before the cohort cut. `n_not_started_by_the_cut`: neither. `n_cohort_unknown`: the campaign stamped no cut."""
    allowed = set(cfg["blocks"]["primary"])
    cols = ["block", "option", "layout", "model"]
    side = {True: "n_not_finished_in_cohort", False: "n_not_started_by_the_cut", None: "n_cohort_unknown"}
    counts = [*side.values(), "n_pending", "n_harness_error"]
    rows: dict[tuple, dict] = {}
    for u in acc.unfinished:
        if _why_out(u["block"], bool(u["exclude_from_analysis"]), allowed) is None:
            r = rows.setdefault(tuple(u[c] for c in cols), {**{c: u[c] for c in cols}, **dict.fromkeys(counts, 0)})
            r[side[u["in_cohort"]]] += 1
            r["n_" + u["status"]] += 1
    return pd.DataFrame([rows[k] for k in sorted(rows)], columns=cols + counts)


def unfinished_table(acc: InfraAccount) -> pd.DataFrame:
    """Runs that are neither scored nor exhausted (pending, or a harness error): listed so none vanishes."""
    return pd.DataFrame(list(acc.unfinished), columns=list(UNFINISHED_FIELDS))
