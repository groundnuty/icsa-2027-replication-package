"""The one place that reads `ScoredRow` fields (#14).

If #13 renames or adds a field, only `rows_to_frame` changes. Everything
downstream sees the flat columns listed in `COLUMNS`.
"""
from __future__ import annotations

import collections
import dataclasses
import json
import math
import pathlib
from typing import Iterable

import pandas as pd

from icsa.analysis.config import Config
from icsa.records import Layout, OmissionLabel, Option, RunId, ScoredRow, Termination, first_request_cut

COLUMNS = [
    "run_key", "block", "instance_id", "region_id", "option", "layout", "model", "seed",
    "event_free", "termination", "finished", "label", "time_cap", "unknown",
    "omit", "omit_lower", "omit_upper", "undis", "undis_lower", "undis_upper", "end_to_end_upper", "in_bounds_denominator", "disclosed",
    "coverage_baseline", "coverage_target", "coverage_baseline_lower", "coverage_target_lower", "coverage_baseline_upper",
    "coverage_target_upper", "event_f1", "false_alarm", "end_to_end", "log2_tokens", "log2_tokens_upper", "input_tokens_observed", "output_tokens_observed",
    "input_tokens", "output_tokens", "usage_complete", "first_request_cut", "wall_time_s", "bytes_between_sites",
    "bytes_into_context", "tokens_into_context", "backend", "slot", "system_fingerprint",
    "import_errors", "saw_data_error", "data_error_sources", "label_raw", "routed_to_inspection", "budget_out", "budget_unknown",   # tracer flag (True / False / None) and the outside counts (dict / None)
    "label_instrument", "instrument_unknown", "label_source", "raw_omitting_unknown_not_by_rule",
    "log2_bytes",
    "mask_dim_alias", "mask_strict_invalid_reason",   # amendment 36(d): the mask read through the latitude/longitude alias, and the strict reading's verdict (None: a row scored before 36)
    "coder_pair",      # amendment 26(j): the pair that coded the run (sol+opus | opus+sonnet); None where the run was not inspected or no pair is recorded
]

# Where a finished run's primary label comes from (amendment 11, rubric §8): the instrument decided it; inspection resolved an
# instrument `unknown`; inspection left it unknown; or the run was never inspected (no decision on record: it stays unknown).
LABEL_SOURCES = ("instrument", "inspection", "unresolved", "not_inspected")


def routed_by_rule(r: ScoredRow) -> bool:
    """Amendment 19(a), the labeller's own rule (icsa/instruments/labeller.py, route_loaded_not_used): an `omitting` whose only cause is
    data loaded but not analysed goes to inspection. Read from the raw label and its reasons, never from a later label, so a routed run
    stays routed after inspection resolves it."""
    reasons = r.label_reasons or []
    return r.label_raw is OmissionLabel.OMITTING and "loaded_not_used" in reasons and "not_loaded" not in reasons


def primary_label(r: ScoredRow) -> OmissionLabel | None:
    """H1's primary label: after inspection where the coders resolved or kept an instrument `unknown`, else the instrument's."""
    return r.label_after_inspection if r.label_after_inspection is not None else r.label


def label_source(r: ScoredRow) -> str | None:
    if not r.finished or r.termination is Termination.TIME_CAP:
        return None
    if r.label in (OmissionLabel.COMPLETE, OmissionLabel.OMITTING):
        return "instrument"
    if r.label_after_inspection is None:
        return "not_inspected"
    return "unresolved" if r.label_after_inspection is OmissionLabel.UNKNOWN else "inspection"


def _nan(x: float | None) -> float:
    return float("nan") if x is None else float(x)


def exclusion_reason(r: ScoredRow, allowed: set[str]) -> str | None:
    """Why the analysis leaves a row out, or None if it stays.

    A row is out when the campaign flagged it (`exclude_from_analysis`) OR its block is not in
    `allowed`: either marker alone is enough, so no row passes on the other's say-so. A row with no
    block cannot be placed at all and is an error: dropping it silently could empty the analysis,
    and defaulting it to "main" would let a pilot row through.
    """
    if r.block is None:
        raise ValueError(f"run {r.run.key()} has no block: the scoring step must carry the run record's "
                         "block (and exclude_from_analysis) into ScoredRow")
    if r.infra_failure:
        raise ValueError(f"run {r.run.key()} (block {r.block}) scores attempt {r.attempt}, which ended in an "
                         "infrastructure failure: per-run outcomes use the first attempt without one")
    if r.exclude_from_analysis:
        return "flagged"
    if r.block not in allowed:
        return "block"
    if r.out_of_cohort:          # started at or after the cohort cut: reported apart (exhibits.out_of_cohort_table), never in the paper's contrasts
        return "out_of_cohort"
    return None


def select_rows(rows: Iterable[ScoredRow], cfg: Config,
                blocks: Iterable[str] | None = None) -> tuple[list[ScoredRow], pd.DataFrame]:
    """The rows of `blocks` (default: the pre-registered primary blocks) and a per-block account.

    The account has one line per (block, status), status in kept | flagged | block | out_of_cohort, so a misnamed
    block shows up as a count, not as a silent loss.
    """
    allowed = set(cfg["blocks"]["primary"] if blocks is None else blocks)
    kept: list[ScoredRow] = []
    count: collections.Counter = collections.Counter()
    for r in rows:
        why = exclusion_reason(r, allowed)
        count[(r.block, "kept" if why is None else why)] += 1
        if why is None:
            kept.append(r)
    acct = pd.DataFrame([{"block": b, "status": s, "n": n} for (b, s), n in sorted(count.items())],
                        columns=["block", "status", "n"])
    return kept, acct


def rows_to_frame(rows: Iterable[ScoredRow], cfg: Config, blocks: Iterable[str] | None = None) -> pd.DataFrame:
    """One flat record per run. Option/layout are plain strings.

    Only runs of the primary blocks (`[blocks].primary`: main, pagination) enter; pass `blocks`
    for another selection (see `pilot_frame`). The pilot is a block, not a list of instances: its
    10 instances are also main instances, whose main-block runs stay in.
    """
    rows, _ = select_rows(rows, cfg, blocks)
    recs = []
    for r in rows:
        # H1's primary label is the one after inspection (amendment 11, rubric §8); `r.label` stays the instrument's
        lab = primary_label(r)
        label = lab.value if lab is not None else None
        term = r.termination.value
        # protocol/report-spec.md, "Outcome definitions and bounds": among finished runs the
        # instrument labels C / O / U; K = runs ended by the time cap (a class of their own).
        K = r.termination is Termination.TIME_CAP
        fin = bool(r.finished) and not K
        is_o = fin and lab is OmissionLabel.OMITTING
        is_c = fin and lab is OmissionLabel.COMPLETE
        is_u = fin and not (is_o or is_c)                  # unknown, or finished without a usable label
        # the instrument's own `unknown` (before inspection): its stored coverage is never a point estimate (amendment 19(f))
        inst_unknown = fin and r.label not in (OmissionLabel.COMPLETE, OmissionLabel.OMITTING)
        routed = fin and routed_by_rule(r)
        if routed and r.label is not OmissionLabel.UNKNOWN:
            raise ValueError(f"run {r.run.key()} (block {r.block}): its raw label and reasons say the instrument routed it to inspection "
                             f"(labeller.route_loaded_not_used), but the instrument's label is {r.label}: the record contradicts the rule")
        claim = r.self_report_complete is True             # the report says complete == true
        nan = float("nan")
        first_cut = first_request_cut(r)         # no completed request on record (icsa.records)
        resolved_complete = r.label_after_inspection is OmissionLabel.COMPLETE
        total = sum(getattr(r, f) for f in cfg["outcomes"]["tokens_fields"])
        if first_cut or (not r.usage_complete and (r.cut_request_input is None or r.cut_request_output is None)):
            upper_tokens = nan
        else:
            upper_tokens = math.log2(max(1, total + (0 if r.usage_complete else r.cut_request_input + r.cut_request_output)))
        omit = float(is_o) if (is_o or is_c) else nan      # O / (O + C)
        in_den = fin or K                                  # O + C + U + K
        omit_lower = float(is_o) if in_den else nan
        omit_upper = float(is_o or is_u or K) if in_den else nan
        unknown = is_u
        # undisclosed omission: O' / (O + C + U - U'); K excluded; U' = unknown runs claiming complete
        o_prime, u_prime = is_o and claim, is_u and claim
        undis = float(o_prime) if (is_o or is_c or (is_u and not claim)) else nan
        undis_lower = float(o_prime) if fin else nan       # O' / (O + C + U)
        undis_upper = float(o_prime or u_prime) if fin else nan   # (O' + U') / (O + C + U)
        # end-to-end over ALL runs: finished, label C, correct (the primary label as everywhere else, never the self-report)
        correct = bool(r.correct)
        e2e = float(bool(r.finished) and lab is OmissionLabel.COMPLETE and correct)
        e2e_up = float(bool(r.finished) and lab in (OmissionLabel.COMPLETE, OmissionLabel.UNKNOWN) and correct)
        time_cap = K
        # disclosed iff the self-report says complete == false; None is not disclosed
        disclosed = float("nan") if r.self_report_complete is None else float(r.self_report_complete is False)
        recs.append({
            "run_key": r.run.key(), "block": r.block, "instance_id": r.run.instance_id, "region_id": r.region_id,
            "option": r.run.option.value, "layout": r.run.layout.value, "model": r.run.model,
            "seed": r.run.seed, "event_free": bool(r.event_free), "termination": term,
            "finished": bool(r.finished), "label": label, "time_cap": bool(time_cap),
            "unknown": bool(unknown), "omit": omit, "omit_lower": omit_lower, "omit_upper": omit_upper,
            "undis": undis, "undis_lower": undis_lower, "undis_upper": undis_upper, "end_to_end_upper": e2e_up,
            "in_bounds_denominator": bool(in_den), "disclosed": disclosed,
            # a run the instrument left unknown has no point estimate unless inspection gave it one (both coders' extractions agree
            # exactly), whatever a stored row holds and whatever its label after inspection
            "coverage_baseline": float("nan") if inst_unknown and r.coverage_source != "inspection" else _nan(r.coverage_baseline),
            "coverage_target": float("nan") if inst_unknown and r.coverage_source != "inspection" else _nan(r.coverage_target),
            "coverage_baseline_lower": _nan(r.coverage_baseline_lower), "coverage_target_lower": _nan(r.coverage_target_lower),
            # 26(h), changing 19(f): 1 for a run resolved `complete` (known only after inspection); every other run has the instrument's bound, which the scorer
            # carries (1 on lost read tracking, the loaded extent otherwise; an instrument-labelled complete keeps its own)
            "coverage_baseline_upper": 1.0 if resolved_complete else _nan(r.coverage_baseline_upper),
            "coverage_target_upper": 1.0 if resolved_complete else _nan(r.coverage_target_upper),
            "event_f1": _nan(r.event_f1) if (r.finished and not r.event_free) else float("nan"),
            "false_alarm": _nan(None if r.false_alarm is None else float(r.false_alarm)) if (r.finished and r.event_free) else float("nan"),
            "end_to_end": e2e,
            # Science, #34 (21:41Z, 21:45Z): a run cut mid-request counts at its completed requests' tokens, flagged (`usage_complete` False; the tables beside
            # the cost table and the sensitivity row leave the flagged runs out). A run cut in its FIRST request has no completed request on record, so no tokens:
            # it stays out (NaN), where it would read as log2(max(1, 0)) = 0 tokens.
            "log2_tokens": nan if first_cut else math.log2(max(1, sum(getattr(r, f) for f in cfg["outcomes"]["tokens_fields"]))),
            "input_tokens": nan if first_cut else r.input_tokens, "output_tokens": nan if first_cut else r.output_tokens,
            "usage_complete": bool(r.usage_complete), "first_request_cut": bool(first_cut),
            # 26(d): a run cut after completed requests at its upper bound: those tokens plus the cut request's input and output (the scorer's bound, from the
            # run record). A first-request cut stays out; a cut run whose row records no bound is out too, never at its completed tokens, which would pass for it.
            "log2_tokens_upper": upper_tokens,
            "input_tokens_observed": r.input_tokens, "output_tokens_observed": r.output_tokens,
            "wall_time_s": r.wall_time_s, "bytes_between_sites": _nan(r.bytes_between_sites),
            # H4's descriptive table: bytes on the log2 scale, like tokens (unknown or 0 bytes: no value)
            "log2_bytes": math.log2(r.bytes_between_sites) if r.bytes_between_sites else nan,
            "bytes_into_context": r.bytes_into_context, "tokens_into_context": _nan(r.tokens_into_context),
            "backend": getattr(r, "backend", None) or "unknown",
            "slot": getattr(r, "slot", None) or "unknown",
            # a run the provider served from two builds counts as that pair, not as either
            "system_fingerprint": "+".join(sorted(getattr(r, "system_fingerprints", None) or [])) or "unknown",
            "saw_data_error": getattr(r, "agent_saw_data_error", None),
            "data_error_sources": getattr(r, "data_error_sources", None),
            "import_errors": r.import_errors,
            # amendment 19(a): an `omitting` the instrument routed to inspection because its only cause was loaded_not_used; from the raw
            # label and the reasons, so it stays routed whatever inspection decides
            "label_raw": r.label_raw.value if r.label_raw is not None else None,
            "routed_to_inspection": bool(routed),
            "label_instrument": r.label.value if r.label is not None else None,
            "instrument_unknown": bool(inst_unknown),
            "label_source": label_source(r),
            "coder_pair": r.coder_pair,
            # amendment 36(d): the strict reading beside the lenient one; a row scored before 36 has neither (None, never False)
            "mask_dim_alias": getattr(r, "mask_dim_alias", None), "mask_strict_invalid_reason": getattr(r, "mask_strict_invalid_reason", None),
            # a raw `omitting` the instrument left unknown although the routing rule does not apply: counted apart, never as routed
            "raw_omitting_unknown_not_by_rule": bool(fin and r.label_raw is OmissionLabel.OMITTING and r.label is OmissionLabel.UNKNOWN
                                                     and not routed),
            # 19(b): stopped by the tracking budget, or capped by time with tracking work above half of it; a capped run whose work is not on record
            # cannot be shown under half, so it is out too, and counted apart
            "budget_out": bool("tracking_budget" in (r.label_reasons or []) or (K and (r.tracking_work is None or not r.tracking_budget
                                                                                     or r.tracking_work > r.tracking_budget / 2))),
            "budget_unknown": bool(K and (r.tracking_work is None or not r.tracking_budget)),
        })
    df = pd.DataFrame.from_records(recs, columns=COLUMNS)
    # plain object strings: pandas' arrow-backed strings make the many small group/merge steps ~3x slower
    for c in ("run_key", "block", "instance_id", "region_id", "option", "layout", "model", "termination", "label", "backend", "slot",
              "system_fingerprint", "saw_data_error", "data_error_sources", "import_errors", "label_raw", "label_instrument", "label_source", "coder_pair",
              "mask_dim_alias", "mask_strict_invalid_reason"):
        df[c] = df[c].astype(object)
    dup = df.loc[df["run_key"].duplicated(), "run_key"]
    if len(dup):                       # run_key has no block: one run scored twice, or a pilot row labelled main
        raise ValueError(f"{len(dup)} duplicate run keys among the selected rows, e.g. {dup.iloc[0]}")
    return df


def pilot_frame(rows: Iterable[ScoredRow], cfg: Config) -> pd.DataFrame:
    """The pilot block's runs (never flagged ones): the only use of the pilot is the power re-estimate."""
    return rows_to_frame(rows, cfg, blocks=[cfg["blocks"]["pilot"]])


def row_from_dict(d: dict) -> ScoredRow:
    """Rebuild a ScoredRow from `dataclasses.asdict` JSON (enums as values)."""
    d = dict(d)
    run = d.pop("run")
    run = RunId(run["instance_id"], Option(run["option"]), Layout(run["layout"]), run["model"], int(run["seed"]))
    d["termination"] = Termination(d["termination"])
    d["label"] = OmissionLabel(d["label"]) if d.get("label") is not None else None
    d["label_raw"] = OmissionLabel(d["label_raw"]) if d.get("label_raw") is not None else None     # amendment 19(a): an enum, as `label`
    d["label_after_inspection"] = (OmissionLabel(d["label_after_inspection"]) if d.get("label_after_inspection") is not None
                                   else None)                                                    # amendment 11: an enum too
    return ScoredRow(run=run, **d)


def load_jsonl(path: str | pathlib.Path) -> list[ScoredRow]:
    with open(path) as fh:
        return [row_from_dict(json.loads(line)) for line in fh if line.strip()]


def apply_inspection_coverage(rows: list[ScoredRow], records: list[dict]) -> list[ScoredRow]:
    """Science, #2, 08:42Z: a resolved `unknown` run takes its coverage from the coders' extraction when both agree exactly
    (the rubric's rule for the decomposition), and otherwise stays null. One record per run: `block`, `run_key`,
    `both_agree_exactly`, `coverage_baseline`, `coverage_target`. Inspection can't override a definite label, so a record for
    one is an error, as is a record for no run, or an exact agreement with no number."""
    by = {(r.block, r.run.key()): k for k, r in enumerate(rows)}
    out = list(rows)
    for e in records:
        key = (e["block"], e["run_key"])
        if key not in by:
            raise ValueError(f"an inspection record for no scored run: {key}")
        r = out[by[key]]
        if r.label is not OmissionLabel.UNKNOWN:
            raise ValueError(f"run {key}: inspection cannot override {r.label}")
        if e["both_agree_exactly"] is not True:
            if r.coverage_source == "inspection":      # a row that carries an earlier inspection's point: agreement withdrawn, so it is null again
                out[by[key]] = dataclasses.replace(r, coverage_baseline=None, coverage_target=None, coverage_source=None)
            continue
        values = (e["coverage_baseline"], e["coverage_target"])
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 for v in values):
            raise ValueError(f"run {key}: the coders agree exactly and give no coverage: {values}")
        out[by[key]] = dataclasses.replace(r, coverage_baseline=float(values[0]), coverage_target=float(values[1]), coverage_source="inspection")
    return out


@dataclasses.dataclass(frozen=True)
class FidelityRow:
    """One line of #11's `adapter_rows.jsonl` (`icsa.faults.calibrate.write_rows`): a scored scripted run on one record."""
    run: RunId
    block: str | None
    platform_record: dict
    exclude_from_analysis: bool = False


def run_id_from_key(key: str) -> RunId:
    """The inverse of `RunId.key`."""
    parts = key.split("__")
    if len(parts) != 5 or not parts[4].startswith("s"):
        raise ValueError(f"{key!r} is not a run key (instance__option__layout__model__s<seed>)")
    return RunId(parts[0], Option(parts[1]), Layout(parts[2]), parts[3], int(parts[4][1:]))


def load_fidelity_rows(path: str | pathlib.Path) -> list[FidelityRow]:
    """`adapter_rows.jsonl`, which is no `ScoredRow` file: its run is a key and it holds a fault record only (b3 #3)."""
    out = []
    with open(path) as fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            d = json.loads(line)
            try:
                out.append(FidelityRow(run_id_from_key(d["run"]), d["block"], d["platform_record"]))
            except (KeyError, TypeError, ValueError) as e:
                raise ValueError(f"{path}:{n}: not a fidelity row: {e!r}") from e
    return out
