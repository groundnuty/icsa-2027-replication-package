"""Score one run: `score_run` turns a run directory into a `ScoredRow`.

Rules (science agent, binding): a report is valid iff both report.json and
mhw_mask.nc parse, for every option alike; an invalid run is not finished and
has no outcome metrics. A run is *disclosed* iff report `complete == false`
(caveats are never parsed). The mask is canonical (protocol/report-spec.md):
agent events are the maximal runs of days with at least one cell equal to 1,
the units of an event being the mask's 1s on its days, the same construction
as the reference's events. report.json `events` is only compared with them
(`events_inconsistent`). A false alarm is any sea cell-day equal to 1.
Scoring uses sea cells only (land 1s are counted in `land_cells_set`, nothing
else); "correct" is cell-day IoU >= the protocol threshold (no false alarm on
event-free instances). Events match maximum-cardinality first, overlap second.
"""
from __future__ import annotations

from pathlib import Path

from .. import cutrequest as cut_request
from ..extent import PartedExtent
from ..records import OmissionLabel, Option, RunRecord, ScoredRow, Termination
from . import events, masks, reference
from .config import ScoringConfig
from .cost import run_cost
from .extent_account import extent_account
from .import_errors import import_errors
from .parser_version import parser_version
from .reference import Reference
from .report import parse_run_output


def _count(d: dict | None, k: str) -> int | None:
    v = d.get(k) if isinstance(d, dict) else None
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None


def score_run(record: RunRecord, run_dir: str | Path, ref: Reference,
              analysed: PartedExtent | None, label: OmissionLabel | None,
              platform_record: dict | None = None,
              config: ScoringConfig = ScoringConfig(), *,
              agent_saw_data_error: bool | None = None, coverage_upper: dict | None = None,
              label_raw: OmissionLabel | None = None, label_reasons: list[str] | None = None,
              tracking: dict | None = None, escape_kinds: dict[str, int] | None = None) -> ScoredRow:
    cost = run_cost(record)
    cut = cut_request.of_record(record)          # the bound on the request a cut run was in (amendment 26(d))
    out = parse_run_output(Path(run_dir) / record.output_dir, ref.box, ref.target_days)
    # report-spec: finished iff the run ended with its final message (REPORT) before a
    # cap or terminal harness failure, and both files are valid
    finished = out.valid and record.termination == Termination.REPORT
    ev_free = len(ref.gt.events) == 0

    # Coverage comes from #9's extent and is attached to every run that has one, finished
    # or not. Every other outcome metric is None for an unfinished run. The omission LABEL
    # is #9's (COMPLETE, OMITTING or UNKNOWN), carried unchanged for finished runs, never
    # re-derived here; `complete_extent` is a diagnostic from the extents, not the label.
    cov = None if analysed is None else analysed.coverage_of(ref.required)
    # The instrument knows the extent exactly only on a definite label. On unknown it lost track, so the share is a lower
    # bound and no estimate: null, never 0, or a run that analysed everything would count as having analysed nothing.
    exact = cov is not None and label in (OmissionLabel.COMPLETE, OmissionLabel.OMITTING)
    upper = coverage_upper or {}
    complete_extent = cf = cf_omission_f1 = None
    if finished and analysed is not None:
        complete_extent = not analysed.omits(ref.required)
        cf = reference.counterfactual(ref, analysed)
        cf_omission_f1 = events.match_events(      # None if the full-data run has no event
            reference.detection_events(cf, cf.days),
            reference.detection_events(ref.full, ref.full.days)).f1

    m = day_agr = cd_f1 = iou = cf_comp_f1 = false_alarm = inconsistent = None
    land = account = None
    if finished:
        raw = out.mask     # canonical, on the full requested region and period
        land = masks.land_cells(raw, ref.sea)
        mask = raw & ref.sea    # scoring uses sea cells only
        runs = events.active_runs(masks.day_active(mask))
        agent = [events.event_units(mask, i0, i1) for i0, i1 in runs]
        # report.json `events` is a consistency check only, never scored from (multiset)
        derived = [(int(ref.target_days[i0]), int(ref.target_days[i1 - 1])) for i0, i1 in runs]
        inconsistent = sorted(derived) != sorted(out.report.events)
        m = events.match_events(agent, reference.detection_events(ref.gt, ref.gt.days))
        day_agr = masks.day_agreement(mask, ref.gt.cell_mask, ref.sea)
        cd_f1 = masks.cell_day_f1(mask, ref.gt.cell_mask, ref.sea)
        iou = masks.cell_day_iou(mask, ref.gt.cell_mask, ref.sea)
        if ev_free:
            false_alarm = bool(mask.any())      # any sea cell-day equal to 1
        if cf is not None:
            cf_comp_f1 = events.match_events(agent, reference.detection_events(cf, cf.days)).f1
        if analysed is not None:
            account = extent_account(out.report, analysed)

    if not finished:
        correct = None
    elif ev_free:
        correct = not false_alarm
    else:
        correct = iou >= config.correct_iou_threshold

    return ScoredRow(
        run=record.run, region_id=ref.instance.region_id, event_free=ev_free,
        termination=record.termination, finished=finished,
        label=label if finished else None,
        coverage_baseline=cov["baseline"] if exact else None,
        coverage_target=cov["target"] if exact else None,
        # no extent observed (no trace, say) is the widest bound, not a run that drops out of the sensitivity
        coverage_baseline_lower=cov["baseline"] if cov else 0.0, coverage_target_lower=cov["target"] if cov else 0.0,
        coverage_baseline_upper=upper.get("baseline", 1.0), coverage_target_upper=upper.get("target", 1.0),
        coverage_source="instrument" if exact else None,
        self_report_complete=out.report.complete if finished else None,
        event_precision=None if ev_free or m is None else m.precision,
        event_recall=None if ev_free or m is None else m.recall,
        event_f1=None if ev_free or m is None else m.f1,
        false_alarm=false_alarm, day_agreement=day_agr, cell_day_f1=cd_f1,
        cf_computation_f1=cf_comp_f1, cf_omission_f1=cf_omission_f1,
        correct=correct,
        end_to_end=bool(finished and label == OmissionLabel.COMPLETE and correct),
        input_tokens=cost.input_tokens, output_tokens=cost.output_tokens,
        wall_time_s=cost.wall_time_s, bytes_between_sites=cost.bytes_between_sites,
        bytes_into_context=cost.bytes_into_context, tokens_into_context=cost.tokens_into_context,
        platform_record=platform_record,
        import_errors=import_errors(record.turns), usage_complete=record.usage_complete, requests_completed=len(record.turns),
        cut_request_input=(cut or (None, None))[0], cut_request_output=(cut or (None, None))[1],
        parser_commit=parser_version()["commit"], parser_sha256=parser_version()["sha256"],
        report_valid=out.report_valid, mask_valid=out.mask_valid,
        invalid_reason=(out.reasons.get("report") or out.reasons.get("mask")
                        or (None if finished else f"termination_{record.termination.value}")),
        report_invalid_reason=out.reasons.get("report"),
        mask_invalid_reason=out.reasons.get("mask"),
        mask_dim_alias=out.mask_dim_alias, mask_strict_invalid_reason=out.mask_strict_reason,   # amendment 36(c)/(d): recorded, never the verdict
        disclosed=(not out.report.complete) if finished else None,
        complete_extent=complete_extent,
        n_agent_events=m.n_agent if m else None, n_ref_events=len(ref.gt.events),
        merges=m.merges if m else None, splits=m.splits if m else None,
        events_inconsistent=inconsistent, cell_day_iou=iou,
        land_cells_set=land[0] if land else None, land_cell_days_set=land[1] if land else None,
        extent_account=account, backend=getattr(record, "backend", None),
        slot=record.extras.get("slot"), system_fingerprints=record.extras.get("system_fingerprints"),
        # campaign fields (#16): which block the run belongs to and whether every analysis drops it
        exclude_from_analysis=bool(getattr(record, "exclude_from_analysis", False)),
        out_of_cohort=bool(getattr(record, "out_of_cohort", False)),
        label_raw=label_raw if finished else None, label_reasons=list(label_reasons) if label_reasons is not None else None,
        tracking_work=_count(tracking, "work"), tracking_budget=_count(tracking, "budget"), escape_kinds=escape_kinds,
        site_g_settings_sha256=getattr(record, "site_g_settings_sha256", None),
        block=getattr(record, "block", None),
        attempt=int(getattr(record, "attempt", 1)),
        infra_failure=bool(getattr(record, "infra_failure", False)),
        **_agent_seen_errors(record, agent_saw_data_error))


def _tri(v) -> bool | None:
    """A recorded flag as bool, anything else (absent, null) as None: unknown is never False."""
    return v if isinstance(v, bool) else None


REST_OPTIONS = ("T", "T-unpaginated", "D")     # icsa.sandbox.gatepolicy, whose import needs nothing of this package; test_run_evidence checks they agree
GATE_ERROR_KEYS = ("gate_5xx", "gate_resets", "upstream_5xx", "upstream_resets", "client_request_errors")


def _agent_seen_errors(record, agent_saw_data_error: bool | None) -> dict:
    """Inputs of the analysis's data-error flag, None where not recorded (never False): (A) the tracer's flag, passed
    by the pipeline from `label_run`'s flags["agent_saw_data_error"] (or `analyse.data_errors_of(trace_dir)`);
    (B) the gate log's error counts and the sidecar log's FUSE counts (#61), from the record's sandbox metadata."""
    sb = getattr(record, "sandbox", None) or {}
    src: dict = {}
    # only the record this option's definition needs (science's ruling, 2 Nov): a run is `clear` only when that was read. M has no gate, so an older record's gate zeros say
    # nothing about it, and with its sidecar log unreadable they read as `clear`
    option = getattr(getattr(getattr(record, "run", None), "option", None), "value", None)
    errs = (sb.get("gate_transfers") or {}).get("errors")
    if option in (None, *REST_OPTIONS) and isinstance(errs, dict) and all(isinstance(errs.get(k), int) for k in GATE_ERROR_KEYS):
        src.update({k: errs[k] for k in GATE_ERROR_KEYS})
    se = sb.get("sidecar_errors")
    if option not in REST_OPTIONS and isinstance(se, dict) and all(isinstance(se.get(k), int) for k in ("fuse_not_caused_by_agent", "fuse_caused_by_agent")):
        src.update({k: se[k] for k in ("fuse_not_caused_by_agent", "fuse_caused_by_agent")})   # {"unavailable": ...} has neither
    return {"agent_saw_data_error": agent_saw_data_error if isinstance(agent_saw_data_error, bool) else None,
            "data_error_sources": src or None}


def invalid_rates(rows: list[ScoredRow]) -> dict[Option, dict]:
    """Per option, over ALL runs of that option: the share not finished, the share
    with an invalid report and with an invalid mask, and the rate of each reason
    (report reasons, mask reasons and non-report terminations are counted
    separately, so a run can appear under several), so asymmetries are visible."""
    out: dict[Option, dict] = {}
    for opt in sorted({r.run.option for r in rows}, key=lambda o: o.value):
        rs = [r for r in rows if r.run.option == opt]
        n = len(rs)
        reasons: dict[str, float] = {}
        for r in rs:
            for code in (r.report_invalid_reason, r.mask_invalid_reason,
                         None if r.termination == Termination.REPORT else f"termination_{r.termination.value}"):
                if code:
                    reasons[code] = reasons.get(code, 0) + 1 / n
        out[opt] = {"n": n,
                    "report_invalid_rate": sum(not r.report_valid for r in rs) / n,
                    "mask_invalid_rate": sum(not r.mask_valid for r in rs) / n,
                    "unfinished_rate": sum(not r.finished for r in rs) / n,
                    "reasons": reasons}
    return out
