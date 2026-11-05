"""Shared record types: options, layouts, instances, the run record (#8 writes
it; #9, #11 and #13 read it) and the scored row (#13 writes it; #14 reads it).

DRAFT. The report schema, its parsing rule and the frozen parameters come
from the science agent under `protocol/`. Field names here may change when
it lands; change them here, in one place, and every module follows.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import json
from typing import Any


class Option(str, enum.Enum):
    T = "T"                          # official fsspec REST client, range reads
    T_UNPAGINATED = "T-unpaginated"  # T with a complete listing
    D = "D"                          # whole-file download
    M = "M"                          # oneclient mount
    M_PLUS = "M+"                    # M pre-provisioned; scripted runs only


class Layout(str, enum.Enum):
    S1 = "S1"  # 15,340 daily files in one flat directory
    S2 = "S2"  # one file chunked (1, 626, 1051) in time


class Termination(str, enum.Enum):
    REPORT = "report"
    TURN_CAP = "turn_cap"
    TIME_CAP = "time_cap"
    TOKEN_BUDGET = "token_budget"   # added by #8: parameters.md ends a run that exceeds the budget as token_budget
    OUTPUT_CAP = "output_cap"       # added by #8: the last reply stopped on the provider's output-length limit
    ERROR = "error"


class OmissionLabel(str, enum.Enum):
    OMITTING = "omitting"
    COMPLETE = "complete"
    UNKNOWN = "unknown"


@dataclasses.dataclass(frozen=True)
class Period:
    start: dt.date
    end: dt.date  # inclusive


@dataclasses.dataclass(frozen=True)
class Instance:
    """One task instance (#5): a region and a target period."""

    instance_id: str
    region_id: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    lat0: int  # cell index ranges, half-open, as icsa.extent.CellBox
    lat1: int
    lon0: int
    lon1: int
    target: Period
    pilot: bool = False
    # #5's calibration flag: the one event-bearing pilot instance the 42-run calibration
    # block uses (closest to the pilot median of reference events; parameters.md)
    calibration: bool = False


@dataclasses.dataclass(frozen=True)
class RunId:
    instance_id: str
    option: Option
    layout: Layout
    model: str  # the name we report; the API id goes in RunRecord.model_api_id
    seed: int

    def key(self) -> str:
        return f"{self.instance_id}__{self.option.value}__{self.layout.value}__{self.model}__s{self.seed}"


@dataclasses.dataclass
class Turn:
    index: int
    input_tokens: int
    output_tokens: int
    tool_calls: list[dict[str, Any]]      # name, arguments, as sent by the model
    tool_outputs: list[str]               # exactly as delivered, after capping
    bytes_into_context: int
    tokens_into_context: int | None       # provider-tokenizer count of the tool outputs; None where none exists (see extras)
    # additive, model-independent measures of what the tool results delivered (primary):
    chars_into_context: int = 0
    tool_output_chars: list[int] = dataclasses.field(default_factory=list)   # per tool result
    tool_output_bytes: list[int] = dataclasses.field(default_factory=list)   # UTF-8 bytes per tool result
    # Claude prompt caching (additive): input_tokens above is the whole prompt =
    # uncached_input_tokens + cache_creation_input_tokens + cache_read_input_tokens.
    # None / 0 for models that report no split.
    uncached_input_tokens: int | None = None
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclasses.dataclass
class RunRecord:
    """Everything one run leaves behind (#8). Paths are relative to the run dir."""

    run: RunId
    started_at: str                       # ISO 8601 UTC
    ended_at: str
    termination: Termination
    error_type: str | None
    model_api_id: str
    endpoint: str
    model_version: str | None
    seed_honoured: bool                   # False where the API has no seed
    temperature: float
    turns: list[Turn]
    transcript_path: str                  # full transcript, as sent and received
    code_cells_path: str                  # every code cell the agent ran
    output_dir: str                       # output/report.json, output/mhw_mask.nc
    wall_time_s: float
    concurrency_at_start: int
    site_id: str
    provider_id: str
    harness_commit: str
    sandbox: dict[str, Any]               # #7: option, client/library versions, I/O mode, cache-clear evidence
    extras: dict[str, Any] = dataclasses.field(default_factory=dict)
    # additive (after the first release of the record): where the model was served, and malformed-call count
    backend: str | None = None            # "hpc" | "site_b" | "anthropic"
    base_url: str | None = None
    usage_complete: bool = True           # False when a request was abandoned: its token usage is unknown
    provider_cap: int | None = None       # the effective concurrency cap of the provider pool at this run's start
    invalid_tool_args_rounds: int = 0     # tool rounds in which >= 1 call had unparseable arguments (#17 cause coding)
    # Campaign fields (#16), additive. Set by icsa.campaign; defaults suit a bare #8 run.
    attempt: int = 1                      # infra-failure attempt number (same seed), 1..3
    infra_failure: bool = False           # attempt ended by a failure outside the agent's control
    infra_reason: str | None = None       # kind (endpoint | sandbox | onedata_health) and detail
    out_of_cohort: bool = False           # started at or after the cohort cut: kept and reported descriptively, out of the paper's cohort (science, #2, 2 Nov)
    exclude_from_analysis: bool = False   # calibration rows: every analysis drops them (#14 filters on this)
    block: str | None = None              # pilot | main | pagination | optional_*
    site_g_settings_sha256: str | None = None  # the hash of site_g's Traefik and op_worker settings when the run was dispatched (None = not checked)
    opw_restart_no: int | None = None     # op_worker restarts finished when the run was dispatched (icsa.opwrestart; None = not stamped)

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), default=_json_default, indent=1)


@dataclasses.dataclass
class ScoredRow:
    """One row per run for the analysis (#14). None where undefined."""

    run: RunId
    region_id: str
    event_free: bool
    termination: Termination
    finished: bool                        # the frozen parser accepted report.json
    label: OmissionLabel | None           # #9; None if not finished
    coverage_baseline: float | None
    coverage_target: float | None
    self_report_complete: bool | None     # report.json `complete`
    event_precision: float | None
    event_recall: float | None
    event_f1: float | None                # undefined on event-free instances
    false_alarm: bool | None              # event-free instances only
    day_agreement: float | None
    cell_day_f1: float | None
    cf_computation_f1: float | None       # agent output vs counterfactual
    cf_omission_f1: float | None          # counterfactual vs full-data reference
    correct: bool | None                  # against the protocol threshold
    end_to_end: bool                      # finished and complete and correct
    input_tokens: int
    output_tokens: int
    wall_time_s: float
    bytes_between_sites: int | None
    bytes_into_context: int
    tokens_into_context: int | None       # None: not counted (extras' tokens_into_context_reason), never zero
    platform_record: dict[str, Any] | None = None  # #11 detector output
    # --- additive fields from #13 (all defaulted; none renamed or removed) ---
    report_valid: bool = False            # report.json parsed
    mask_valid: bool = False              # mhw_mask.nc parsed (finished = report_valid and mask_valid)
    invalid_reason: str | None = None     # first failure (report, then mask, then termination)
    report_invalid_reason: str | None = None  # why report.json failed, if it did
    mask_invalid_reason: str | None = None    # why mhw_mask.nc failed, if it did (kept even when the report failed too)
    # Amendment 36(c)/(d), additive: the mask's dims were read through the latitude/longitude alias (valid or not), and its
    # verdict under the registered strict reading ("mask_invalid" when the alias was used; else the mask's own reason, None
    # if valid), so tables can show both. The lenient reading is the verdict (mask_valid, finished); these only record.
    mask_dim_alias: bool | None = None
    mask_strict_invalid_reason: str | None = None
    disclosed: bool | None = None         # complete == false in the report; caveats are never parsed
    complete_extent: bool | None = None   # analysed extent covers the required one (the "complete" of end_to_end)
    n_agent_events: int | None = None
    n_ref_events: int | None = None
    merges: int | None = None             # agent events overlapping >= 2 reference events
    splits: int | None = None             # reference events overlapped by >= 2 agent events
    events_inconsistent: bool | None = None  # report.json events differ from the mask-derived ones
    cell_day_iou: float | None = None     # agent vs reference cell-day masks (sea cells); basis of `correct`
    land_cells_set: int | None = None     # distinct land cells the mask sets to 1 (inconsistency; scores ignore them)
    land_cell_days_set: int | None = None
    # Coverage (science, #2, 08:42Z): coverage_baseline and coverage_target are the point estimate, the instrument's exact
    # extent on complete and omitting, and null on unknown, never 0. These bounds hold for every run, unknown too.
    coverage_baseline_lower: float | None = None   # the instrument's lower extent
    coverage_target_lower: float | None = None
    coverage_baseline_upper: float | None = None   # the instrument's upper bound on what can have reached the outputs
    coverage_target_upper: float | None = None
    coverage_source: str | None = None    # of the point estimate: instrument | inspection (both coders' extractions agreed exactly)
    usage_complete: bool = True           # False: a request was abandoned, so input_tokens and output_tokens are what was observed
    requests_completed: int | None = None  # the turns on record (each has usage); 0 with usage_complete False = cut in the FIRST request; None = not recorded
    # amendment 26(c), (d): the bound on the request a run was cut in, in tokens (icsa.cutrequest): its input and its output. Set by the scorer for a run cut after
    # completed requests; None for a complete run, a first-request cut, and a row that did not record it.
    cut_request_input: int | None = None
    cut_request_output: int | None = None
    import_errors: dict[str, int] | None = None   # module -> tool outputs that ended in its ImportError; None: no turn recorded
    parser_commit: str | None = None      # the frozen parser's commit (report spec); None: a tree with no git history
    parser_sha256: str | None = None      # the hash of its content, always there
    backend: str | None = None           # model backend of the run (hpc | site_b), from the run record; None if unrecorded
    slot: str | None = None              # the model slot that served the run, from the run record; None if unrecorded
    system_fingerprints: list[str] | None = None  # the builds the provider reported during the run, from the run record; None if unrecorded
    extent_account: dict[str, Any] | None = None  # report's own extent vs the instrumented envelope (descriptive)
    # Campaign fields (#16), carried from the run record by score_run; the analysis (#14) filters on both.
    out_of_cohort: bool = False           # started at or after the cohort cut: kept and reported descriptively, out of the paper's cohort (science, #2, 2 Nov)
    # amendment 19: the instrument's label before (a)'s routing of a loaded_not_used-only `omitting` to inspection, its reasons, and (b)'s tracking
    # work and the budget it ran under. None: not recorded (an older trace), never a guess.
    label_raw: OmissionLabel | None = None
    label_reasons: list[str] | None = None
    tracking_work: int | None = None
    tracking_budget: int | None = None
    escape_kinds: dict[str, int] | None = None   # the tracer's escapes by kind (scalar, tolist, iter, ...), from its events; None: no trace (science, #2, 17:32Z)
    exclude_from_analysis: bool = False   # calibration rows: every analysis drops them (#14 filters on this)
    block: str | None = None              # pilot | main | pagination | optional_*
    site_g_settings_sha256: str | None = None  # the hash of site_g's Traefik and op_worker settings when the run was dispatched (None = not checked)
    opw_restart_no: int | None = None     # op_worker restarts finished when the run was dispatched (icsa.opwrestart; None = not stamped)
    attempt: int = 1                      # infra attempt this row scores (carried from the record)
    infra_failure: bool = False           # True: a discarded attempt; the analysis refuses such a row
    # Data-path errors the agent saw, of any origin, by ONE concept in every option (science, #7). None = unknown / not recorded.
    agent_saw_data_error: bool | None = None       # (A) the tracer's record (#9: label_run flags), same rule in every option
    # (B) from outside the agent: counts from the gate log (T, T-unpaginated, D: gate_5xx, gate_resets, upstream_5xx,
    # upstream_resets, client_request_errors) and/or from the sidecar log (M: fuse_not_caused_by_agent, fuse_caused_by_agent); None = no source
    data_error_sources: dict[str, Any] | None = None
    # amendment 11, rubric §8: beside label_raw, the label after blind inspection, H1's primary; set only by the analysis from the coders' decisions
    # (icsa.analysis.inspection), and only on a run the instrument left `unknown`. None: not inspected. `label` stays the instrument's.
    label_after_inspection: OmissionLabel | None = None
    # amendment 26(j): which pair coded the run, as the decisions name it (icsa.inspection.plan.PAIR_NAMES: sol+opus | opus+sonnet); set with
    # `label_after_inspection` by the analysis, from the same record. None: not inspected, or an older decisions file that names no pair.
    coder_pair: str | None = None


def first_request_cut(r: ScoredRow) -> bool:
    """A run cut in its FIRST request: its usage is flagged (`usage_complete` False) and no request completed, so it has no tokens (science, #34, 21:45Z).
    By the record's count of completed requests; a row with no count (an older trace) says none completed when it recorded no tokens, since a completed
    request always has input tokens."""
    if r.usage_complete:
        return False
    if r.requests_completed is not None:
        return r.requests_completed == 0
    return r.input_tokens == 0 and r.output_tokens == 0


def _json_default(o: Any) -> Any:
    if isinstance(o, enum.Enum):
        return o.value
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()
    raise TypeError(f"not JSON-serialisable: {type(o).__name__}")
