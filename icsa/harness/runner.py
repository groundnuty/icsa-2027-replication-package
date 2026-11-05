"""Execute one attempt of one run and write its run directory.

`execute_run(run, attempt, run_dir, slot, config)` = fresh sandbox -> prompt -> agent loop ->
collect outputs -> `run_record.json` (a RunRecord) + `transcript.json` + `code_cells.json` + `output/`
in `run_dir`. The campaign (#16) owns ordering, resumption, retries and the choice of `slot`.

Raises `InfraError` (after cleaning up and writing `infra.json` into `run_dir`, with no `run_record.json`)
when the model endpoint keeps failing after the transport retries, or the sandbox or knowledge
server fails outside the agent's code. Everything else, agent-code exceptions, turn/time/token caps,
report outcomes, returns as a RunRecord.
"""
from __future__ import annotations

import asyncio
import dataclasses
import datetime as dt
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from icsa import ncio
from icsa.records import Instance, RunId, RunRecord, Termination

from .adapters import AnthropicAdapter, ModelAdapter, OpenAICompatAdapter
from .config import BASE_COMMIT, BASE_REPO, HarnessConfig, ModelSpec, assert_frozen
from .errors import InfraError
from .knowledge import KnowledgePlane
from .loop import UNATTRIBUTED_KILL, LoopResult, ToolBox, run_agent
from .prompt import PromptTexts, render_prompt
from .report import validate_outputs
from .sandbox_api import SandboxFactory
from .slots import resolve_slot

KNOWLEDGE_START_TIMEOUT_S = 120.0   # a server that never completes MCP initialisation is broken, not slow
REPO = Path(__file__).resolve().parents[2]

# (spec, seed, slot name or None) -> adapter
AdapterFactory = Callable[[ModelSpec, int, str | None], ModelAdapter]
KnowledgeFactory = Callable[[], KnowledgePlane | None]


def harness_commit() -> tuple[str, bool]:
    """(commit, dirty): from git when the tree is a checkout, else from the snapshot's .code-stamp.json (icsa/codestamp.py). Unknown is
    "unknown" and counts as dirty: a tree copied without .git used to record "unknown" with "not dirty"."""
    from icsa import codestamp
    v = codestamp.version(REPO)
    return v["commit"], v["dirty"]


def default_adapter_factory(cfg: HarnessConfig, study: bool = True, check_config: bool = True) -> AdapterFactory:
    if not Path(cfg.anthropic_key_file).expanduser().is_file():     # fail loudly at start-up, not per run
        raise FileNotFoundError(f"Anthropic key file missing: {cfg.anthropic_key_file}")
    def make(spec: ModelSpec, seed: int, slot: str | None) -> ModelAdapter:
        if study:
            assert_frozen(cfg, spec, check_config)
        if spec.kind == "anthropic":
            return AnthropicAdapter(spec, seed, cfg.limits, Path(cfg.anthropic_key_file).expanduser().read_text().strip(),
                                    client_cfg=cfg.client)
        if not slot:
            raise ValueError("open-weight models need a slot")
        s = resolve_slot(cfg, slot)
        key = "none"
        if s.backend == "site_b":                  # read at use time; never logged or recorded
            key = Path(cfg.site_b["key_file"]).expanduser().read_text().strip()
            if not key:
                raise InfraError("endpoint", "site_b key file is empty")
        return OpenAICompatAdapter(spec, s.base_url, s.slot, seed, cfg.limits, cfg.client,
                                   api_key=key, backend=s.backend)
    return make


@dataclasses.dataclass
class RunContext:
    """The `config` argument of execute_run: everything an attempt needs besides its identity."""
    cfg: HarnessConfig
    texts: PromptTexts
    instances: dict[str, Instance]
    sandbox_factory: SandboxFactory
    adapter_factory: AdapterFactory
    knowledge_factory: KnowledgeFactory = lambda: None
    data_config: dict = dataclasses.field(default_factory=dict)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _model_version(spec, info: dict) -> str | None:
    """Version metadata of the backend that served this run (per-backend notes in config), plus the
    system fingerprint(s) actually observed. Never the note of a backend the run did not use."""
    backend = info.get("backend") or ("anthropic" if spec.kind == "anthropic" else "hpc")
    note = spec.version_for(backend)
    fps = info.get("system_fingerprints") or []
    parts = [p for p in (note, f"system_fingerprint: {', '.join(fps)}" if fps else "") if p]
    return "; ".join(parts) or None


async def _count_tool_tokens(adapter, turns) -> tuple[str, str | None]:
    """(source, reason). The token count of the delivered tool results, only where the provider has a tokenizer (vLLM
    /tokenize). Where it has none, or its call fails, the count is None with the reason, never 0: a 0 reads as a result,
    and averages in as one. No figure is derived from usage differences. A run with no tool output delivered nothing."""
    if not any(t.tool_outputs for t in turns):
        return "no tool outputs", None
    counter = getattr(adapter, "count_tokens", None)
    if counter is None:
        reason = "the adapter has no tokenizer"
    else:
        try:
            for t in turns:
                t.tokens_into_context = sum([await counter(x) for x in t.tool_outputs])
            return "provider tokenizer", None
        except Exception as e:  # noqa: BLE001 -- the tokenizer is optional
            reason = f"the tokenizer call failed: {type(e).__name__}"
    for t in turns:
        t.tokens_into_context = None
    return "unavailable", reason


def _host_aliases(sb_meta: dict) -> Any:
    """What the sandbox recorded; a run whose sandbox gave no metadata (a failed start) records what this host is set to."""
    if "host_aliases" in sb_meta:
        return sb_meta["host_aliases"]
    try:
        from icsa.sandbox.config import default_host_aliases
        return dict(sorted(default_host_aliases().items()))
    except Exception as e:  # noqa: BLE001 -- the record of a failed run must still be written
        return {"error": repr(e)[:200]}


def _host_facts(sb_meta: dict) -> dict:
    """Also when the sandbox gave no metadata."""
    if sb_meta.get("host"):
        return sb_meta["host"]
    from icsa.sandbox import hostops
    return hostops.host_facts()


def _instrument_problem(sb_meta: dict) -> str | None:
    """Why this run's instrument record cannot be trusted, for a run that was meant to be traced; None when it can, or when it was not meant to be."""
    inst = sb_meta.get("instrument") or {}
    if not inst.get("configured"):
        return None
    if inst.get("error_at_end") or inst.get("error"):
        return f"the instrument failed: {inst.get('error_at_end') or inst.get('error')}"
    if not inst.get("loaded"):
        return "the instrument did not load"
    if inst.get("loaded_record_bad"):
        return f"the instrument's loaded record says it failed: {inst['loaded_record_bad']}"
    if inst.get("loaded_record_required") and not inst.get("loaded_records"):
        return "the instrument left no loaded record"
    if "trace_files" not in inst or inst["trace_files"] is None:
        return f"the instrument's trace could not be read at the end of the run{': ' + inst['state_error'] if inst.get('state_error') else ''}"
    if inst.get("cells") and not inst["trace_files"]:
        return f"the instrument wrote nothing in {inst['cells']} cells"
    # the probes at the start leave files, so that check above can pass with every cell untraced. The harness knows what it launched; what the agent launched is the labeller's
    if inst.get("start_markers") is not None and inst.get("cells_completed") is not None and inst["start_markers"] < inst["cells_completed"]:
        return f"{inst['cells_completed']} cells ran and the tracer started in {inst['start_markers']} of them"
    return None


def _record_problem(sb_meta: dict, option_is_rest: bool) -> str | None:
    """Why this run's records cannot stand for it (science's ruling, 2 Nov: a missing or failed record makes the run invalid and retried, never `omitting` or `clear`).
    None when they can. A kill the sandbox found only at the end, with no cell left to raise it, is here too.

    First, a gate or sidecar that died, restarted or was OOM-killed during the run (science's ruling, 2 Nov, #2; amendment 24): read from the container's own state at collection, never from
    what the agent saw fail, and infrastructure only when agent code did not cause it. The sandbox gives each death a cause (icsa.sandbox.infradeath): `host_pressure`, `component_defect` and
    `undetermined` are infrastructure and come here; `own_limit_agent` (the sidecar at its own memory limit) is the agent's outcome and does not. It comes before the records, which a dead
    container leaves short, so the detail names the container, the cause and the evidence rather than a lost log."""
    from icsa.sandbox.infradeath import infra_detail
    dead = infra_detail(sb_meta.get("container_deaths"))
    if dead is None and sb_meta.get("infra_death"):      # a sandbox that gave the list without the causes: not known whose doing it was
        dead = "container death (cause=undetermined): " + "; ".join(sb_meta["infra_death"])
    if dead:
        return dead
    problem = _instrument_problem(sb_meta)
    if problem:
        return problem
    gate = sb_meta.get("gate_transfers") or {}
    if option_is_rest and gate.get("unavailable"):
        return f"the gate's record is lost: {gate['unavailable']}"
    side = sb_meta.get("sidecar_errors")
    own_limit = any(d.get("role") == "sidecar" and d.get("category") == "agent" for d in sb_meta.get("container_deaths") or [] if isinstance(d, dict))
    if not option_is_rest and isinstance(side, dict) and side.get("unavailable") and not own_limit:      # a sidecar the agent's reads killed at its limit has no log to read: its outcome, not a lost record
        return f"oneclient's record is lost: {side['unavailable']}"
    late = [k for k in sb_meta.get("cell_kills") or [] if k.get("category") == "infrastructure"]
    if late:
        return f"{late[0].get('reason')} at cell {late[0].get('cell')}: {late[0].get('basis')}"
    return None


def _unattributed_kill(sb_meta: dict) -> str | None:
    """What the harness lost track of, which the loop may never have seen: retried (science, 2 Nov), and reported per option and model since it may discard an agent's own outcome."""
    unread = sb_meta.get("oom_counters_unreadable_cells")
    if unread:
        return f"the memory counters could not be read after cell(s) {unread[:8]}: not known whether a process was killed"
    unsampled = sb_meta.get("earlyoom_unsampled_kills_of_this_uid")
    if unsampled:
        return f"earlyoom killed {len(unsampled)} process(es) of the agents' uid during this run that no sandbox here ever saw: it may have been this run's"
    late = [k for k in sb_meta.get("cell_kills") or [] if k.get("category") == "unknown"]
    return f"{late[0].get('reason')} at cell {late[0].get('cell')}: {late[0].get('basis')}" if late else None


def _run_cause(kills: list[dict], sb_meta: dict) -> str | None:
    """The one cause of this run's kills, from the sandbox's own record as well as what the loop saw (killcause.py has the order): the sandbox's has the kills no cell reported."""
    from icsa.sandbox.killcause import run_cause
    reasons = [k.get("reason") for k in kills] + [k.get("reason") for k in sb_meta.get("cell_kills") or []]
    return run_cause(reasons + (["earlyoom"] if sb_meta.get("earlyoom_kills") else []) + (["container_dead"] if sb_meta.get("infra_death") else []))


def _kill_summary(kills: list[dict], sb_meta: dict) -> dict:
    """Cells of this run that were killed or timed out, as the agent's harness saw them, by cause and by category (the
    sandbox's own record, with the cgroup facts, is in `sandbox.cell_kills`). Reported per option by the dossier and the status."""
    by_reason: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for k in kills:
        by_reason[k["reason"]] = by_reason.get(k["reason"], 0) + 1
        by_category[k["category"]] = by_category.get(k["category"], 0) + 1
    return {"total": len(kills), "by_reason": by_reason, "by_category": by_category, "cause": _run_cause(kills, sb_meta), "cells": kills}


def _memory_summary(sb_meta: dict) -> dict:
    """The run's memory use as the sandbox measured it; None where it could not be read (never a zero)."""
    keys = ("memory_peak_bytes", "memory_anon_peak_bytes", "memory_max_bytes", "oom_killed", "oom_kill_count", "memory_stat_at_anon_peak")
    return {**{k: sb_meta.get(k) for k in keys},
            "note": "memory_peak_bytes includes file cache and tmpfs; memory_anon_peak_bytes is the sampled anon+shmem maximum (1 s period)"}


def _trace_volume(sandbox) -> dict:
    """The bytes the run's /trace used and the volume's size (science, #34, 18:31Z), as the sandbox measured them. None with a reason where it did not: a stand-in without the
    method, a sandbox that never started, a measurement that failed. Never 0, and never a failure of the run."""
    fn = getattr(sandbox, "trace_usage", None)
    why = "no sandbox was started" if sandbox is None else "the sandbox has no trace_usage"
    if fn is not None:
        try:
            got = fn()
            if isinstance(got, dict) and {"trace_used_bytes", "trace_size_bytes", "trace_usage_reason"} <= set(got):
                return {k: got[k] for k in ("trace_used_bytes", "trace_size_bytes", "trace_usage_reason")}
            why = "trace_usage returned no figures"
        except Exception as e:  # noqa: BLE001 -- the measurement must never fail the run
            why = f"trace_usage failed: {type(e).__name__}: {e}"
    return {"trace_used_bytes": None, "trace_size_bytes": None, "trace_usage_reason": why[:300]}


async def _start_sandbox(factory, *args):
    """Run the (blocking, possibly slot-waiting) factory in a worker thread. If this run is cancelled meanwhile (also by the
    loop shutting down), the worker cannot be interrupted: the cancellation is recorded under a lock the worker also takes,
    so whichever comes second stops the sandbox -- it is never left for nobody (and its slot is released by its stop)."""
    import threading
    lock = threading.Lock()
    st: dict = {"cancelled": False, "sandbox": None, "taken": False}

    def worker():
        sb = factory(*args)
        with lock:
            if not st["cancelled"]:
                st["sandbox"] = sb
                return sb
        _quiet(sb.stop)                                   # the run was cancelled while the factory ran
        return None

    try:
        sb = await asyncio.shield(asyncio.ensure_future(asyncio.to_thread(worker)))
        with lock:
            st["taken"] = True
        return sb
    except asyncio.CancelledError:
        with lock:
            st["cancelled"] = True
            late, st["sandbox"] = (st["sandbox"] if not st["taken"] else None), None
        if late is not None:                              # the worker had already finished and nobody will use it
            threading.Thread(target=_quiet, args=(late.stop,), daemon=False).start()    # not on the event loop: stop() blocks
        raise


def _quiet(fn):
    try:
        fn()
    except Exception:  # noqa: BLE001 -- a failed stop quarantines the slot (bind_lease); nothing more to do here
        pass


async def execute_run(run: RunId, attempt: int, run_dir: Path, slot: str | None, config: RunContext,
                      concurrency_at_start: int = 1, provider_cap: int | None = None) -> RunRecord:
    ctx, cfg = config, config.cfg
    spec = cfg.model(run.model)
    if provider_cap is None:                       # records never hold null: default to the configured cap
        provider_cap = cfg.provider_concurrency.get(cfg.concurrency_unit(spec))
    instance = ctx.instances[run.instance_id]
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    out_dir = run_dir / "output"
    commit, dirty = harness_commit()
    started, t0 = _now(), time.monotonic()
    sandbox = adapter = None
    # A run is not started on a model setup that cannot be used (unfrozen settings, a missing key, a bad slot): that is a
    # configuration error, raised as such (the campaign records a terminal harness error), never an "error" run record.
    adapter = ctx.adapter_factory(spec, run.seed, slot)
    result: LoopResult | None = None
    infra: InfraError | None = None
    term, err = Termination.ERROR, None
    info: dict[str, Any] = {}
    transcript: list = []
    sb_meta: dict = {}
    onedata_slot: dict | None = None
    byte_counts: dict = {}
    trace_volume = _trace_volume(None)
    try:
        info = adapter.info()
        try:
            # in a worker thread: the factory may wait for a free Onedata slot user, and runs that share this loop must keep
            # running meanwhile (the one holding the slot has to finish to free it, and every deadline keeps advancing)
            sandbox = await _start_sandbox(ctx.sandbox_factory, run.key(), run.option, run.layout, ctx.data_config)
        except Exception as e:  # noqa: BLE001 -- the sandbox could not start: not the agent's doing
            raise InfraError("sandbox", f"start failed: {type(e).__name__}: {e}"[:500]) from e
        system, user = render_prompt(ctx.texts, instance, run.option, cfg.limits, cfg.slots_for(run.layout))
        try:
            kp = ctx.knowledge_factory()
        except Exception as e:  # noqa: BLE001 -- the knowledge plane could not be built (e.g. its token was refused): not the agent's doing, never a "run"
            raise InfraError("knowledge", f"factory failed: {type(e).__name__}: {e}"[:500]) from e
        failed = False                              # tracked explicitly: sys.exc_info() may show a caller's exception
        try:
            if kp is not None:
                try:
                    await asyncio.wait_for(kp.__aenter__(), timeout=KNOWLEDGE_START_TIMEOUT_S)
                except Exception as e:  # noqa: BLE001
                    kp = None
                    raise InfraError("knowledge", f"start failed: {type(e).__name__}: {e}"[:500]) from e
            result = await run_agent(adapter, ToolBox(sandbox, cfg.limits, kp, agent_memory_gib=cfg.sandbox_limits.agent_memory_gib), system, user, cfg.limits)
        except BaseException:
            failed = True
            raise
        finally:
            # the agent's time ends here, on any exit path: nothing of it goes on computing through what follows. `collect` checks again, and fails the run if it cannot be shown
            quiesce = getattr(sandbox, "quiesce", None)
            if quiesce:
                await asyncio.to_thread(quiesce, "end of the agent loop")
            if kp is not None:
                try:
                    await kp.__aexit__(None, None, None)
                except Exception as e:  # noqa: BLE001 -- teardown must not replace an exception already in flight
                    if not failed:
                        raise InfraError("knowledge", f"teardown failed: {type(e).__name__}: {e}"[:500]) from e
        term, err = result.termination, result.error_type
    except InfraError as e:
        infra = e
        result = getattr(e, "partial", None)
    except Exception as e:  # noqa: BLE001 -- anything else outside the agent: recorded with its type
        term, err = Termination.ERROR, type(e).__name__
        info = info or {"model_api_id": spec.api_id, "endpoint": "", "seed_honoured": spec.seed_supported}
        info["setup_error"] = str(e)[:500]
    except BaseException:                           # cancellation / interrupt: free the sandbox, then re-raise
        for fn in (getattr(sandbox, "stop", None),):
            try:
                if fn:
                    fn()
            except Exception:  # noqa: BLE001
                pass
        if adapter is not None:
            try:
                await adapter.aclose()
            except BaseException:  # noqa: BLE001
                pass
        raise
    cleanup_errors: list[str] = []

    def attempt_step(label: str, fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 -- every cleanup step runs; failures are recorded
            cleanup_errors.append(f"{label}: {type(e).__name__}")
    if adapter is not None:
        info.update(attempt_step("info", adapter.info) or {})   # refresh: retries accrue during the run
        transcript = attempt_step("transcript", adapter.transcript) or []
    if sandbox is not None:
        sb_meta = attempt_step("metadata", sandbox.metadata) or {}
        byte_counts = sandbox.bytes_moved() if hasattr(sandbox, "bytes_moved") else {}      # after the agent has stopped, before the containers go
        trace_volume = _trace_volume(sandbox)       # likewise: the /trace mount is gone after stop
        if any(e.startswith("metadata:") for e in cleanup_errors):       # no record is not a clean record
            infra = infra or InfraError("sandbox", f"the run's sandbox record could not be read ({cleanup_errors[-1]})"[:500])
        from icsa.sandbox.gatepolicy import REST_OPTIONS
        problem = _record_problem(sb_meta, run.option.value in REST_OPTIONS)
        if problem:              # never `omitting` or `clear`
            infra = infra or InfraError("sandbox", problem[:500])
        lost = _unattributed_kill(sb_meta)
        if lost:
            infra = infra or InfraError(UNATTRIBUTED_KILL, lost[:500])
        if sb_meta.get("earlyoom_kills"):      # also a kill the agent never saw fail a cell: its data path went, or it was between cells. First in the order, whatever was noticed before it
            infra = InfraError("sandbox", f"earlyoom killed {len(sb_meta['earlyoom_kills'])} process(es) of this run: "
                                          + ", ".join(sorted({f"{k['comm']} ({k['role']})" for k in sb_meta["earlyoom_kills"]})))
        elif sb_meta.get("earlyoom_log_readable") is False:      # not known whether it was hit: not an outcome
            infra = infra or InfraError("sandbox", "earlyoom's journal could not be read at the end of the run")
        try:
            got = sandbox.collect(run_dir)     # the sandbox contract: dest/output/{report.json,mhw_mask.nc}, dest/cells, dest/trace
            if isinstance(got, dict) and "gate_stop" in got:      # the gate is stopped in collect, after the metadata() above: its note comes back here
                sb_meta["gate_stop"] = got["gate_stop"]
        except Exception as e:  # noqa: BLE001 -- the outputs could not be fetched out of the sandbox
            infra = infra or InfraError("sandbox", f"collect failed: {type(e).__name__}: {e}"[:500])
        try:
            sandbox.stop()
        except Exception as e:  # noqa: BLE001 -- a sandbox that cannot be stopped is infrastructure, and may leak
            infra = infra or InfraError("sandbox", f"stop failed: {type(e).__name__}: {e}"[:500])
        # the Onedata slot user the run's tokens belonged to (released by stop); its bounds bracket the tokens' use
        slot_fn = getattr(sandbox, "onedata_slot", None)
        onedata_slot = slot_fn() if slot_fn else None
    if adapter is not None:
        try:
            await adapter.aclose()
        except Exception as e:  # noqa: BLE001
            cleanup_errors.append(f"aclose: {type(e).__name__}")
    out_dir.mkdir(exist_ok=True)
    if infra is not None:
        try:
            info_now = adapter.info() if adapter is not None else {}      # the usage so far, not the start-of-run snapshot
        except Exception:  # noqa: BLE001
            info_now = {}
        (run_dir / "infra.json").write_text(json.dumps({
            "kind": infra.kind, "detail": infra.detail, "attempt": attempt, "slot": slot, "host_aliases": _host_aliases(sb_meta), "host": _host_facts(sb_meta),
            "cause": _run_cause(result.kills if result else [], sb_meta), "evidence_kept_at": getattr(sandbox, "evidence_kept_at", None),
            # a gate or sidecar that did not survive the run: the state it came up in against the state at collection, per container (an infra attempt leaves no run record to hold it)
            "infra_death": sb_meta.get("infra_death"), "infra_death_cause": sb_meta.get("infra_death_cause"), "container_deaths": sb_meta.get("container_deaths"),
            "infra_containers": sb_meta.get("infra_containers"),
            **trace_volume,         # the bytes the run's /trace used: a run that filled it is retried, and this is its only record
            "turns_completed": len(result.turns) if result else 0, "cleanup_errors": cleanup_errors,
            # every reply the adapter saw, counted when it arrived (a reply that raised after its 200 is billed too); unknown when a request
            # was abandoned or a reply carried no usage. Campaign accounting reads this for an attempt that left no run record.
            "usage_seen": info_now.get("usage_seen"), "usage_complete": bool(info_now) and not info_now.get("abandoned_request") and not info_now.get("usage_missing"),
            "rate_limited_429": info_now.get("rate_limited_429"),
            "onedata_slot": onedata_slot, "transcript": transcript}, indent=1))
        raise infra
    tok_source, tok_reason = await _count_tool_tokens(adapter, result.turns if result else [])   # only for a run that has a record
    if cleanup_errors and err is None:
        term, err = Termination.ERROR, "cleanup_failed"
        if result:
            result.ending = f"error:{err}"
    (run_dir / "transcript.json").write_text(json.dumps(
        {"system_and_messages": transcript, "reasoning": result.reasoning if result else []}, indent=1))
    (run_dir / "code_cells.json").write_text(json.dumps(result.code_cells if result else [], indent=1))
    turns = result.turns if result else []
    ending = result.ending if result else f"error:{err}"
    # Validation is outside the measured window: the wall time is taken here, before it, and any wait for the shared
    # netCDF lock inside it is recorded (never part of wall_time_s or of the time cap, which ended with the agent loop).
    # A wait for a free Onedata slot user happens before the agent loop: it is in neither the time cap nor the wall time.
    slot_wait_s = float((onedata_slot or {}).get("wait_s") or 0.0)
    wall_time_s = time.monotonic() - t0 - slot_wait_s

    def validate_timed():                          # in a worker thread: a wait for the lock must never block the event
        w0 = ncio.thread_wait_s()                  # loop that other runs' agent loops (and their deadlines) share
        res = validate_outputs(out_dir, instance)
        return res, ncio.thread_wait_s() - w0      # thread-local, so this is exactly this validation's wait
    (valid, why), ncio_lock_wait_s = await asyncio.to_thread(validate_timed)
    finished = ending == "final_message" and term is Termination.REPORT and valid       # report-spec.md "Validity"
    rec = RunRecord(
        run=run, started_at=started, ended_at=_now(), termination=term, error_type=err,
        model_api_id=info.get("model_api_id", spec.api_id), endpoint=info.get("endpoint", ""),
        model_version=_model_version(spec, info), seed_honoured=bool(info.get("seed_honoured", False)),
        temperature=float(spec.sampling.get("temperature", float("nan"))),
        turns=turns, transcript_path="transcript.json", code_cells_path="code_cells.json",
        output_dir="output", wall_time_s=wall_time_s,
        concurrency_at_start=concurrency_at_start, provider_cap=provider_cap, site_id=cfg.site_id, provider_id=("site_b" if info.get("backend") == "site_b" else spec.provider_id),
        harness_commit=commit, sandbox=sb_meta,
        backend=info.get("backend", "anthropic" if spec.kind == "anthropic" else None),
        base_url=info.get("endpoint") or None,
        invalid_tool_args_rounds=result.invalid_tool_args_rounds if result else 0,
        usage_complete=not info.get("abandoned_request") and not info.get("usage_missing"),
        extras={
            "host_aliases": _host_aliases(sb_meta), "host": _host_facts(sb_meta),
            "invalid_tool_args_events": result.invalid_tool_args_events if result else [],
            "cell_kills": _kill_summary(result.kills if result else [], sb_meta),
            "memory": _memory_summary(sb_meta),
            "enospc": {"cells": result.enospc_cells if result else [], "count": len(result.enospc_cells) if result else 0,
                       "note": "cells whose output reports ENOSPC: a lower bound (an error the agent's code caught is not seen)"},
            "containers": sb_meta.get("containers"),
            "sandbox_limits": dataclasses.asdict(cfg.sandbox_limits),
            "system_fingerprints": info.get("system_fingerprints", []),
            "rate_limited_429": info.get("rate_limited_429"), "usage_seen": info.get("usage_seen"), "usage_missing": info.get("usage_missing"),
            "served_model_ids": info.get("served_model_ids", []), "served_settings": info.get("served_settings", {}),
            "reasoning_content_seen": info.get("reasoning_content_seen"), "settings_note": info.get("settings_note"),
            "thinking": info.get("thinking"),
            "abandoned_request": info.get("abandoned_request"), "read_timeouts": info.get("read_timeouts", 0),
            "attempt": attempt, "checkpoint": info.get("checkpoint", spec.checkpoint), "slot": info.get("slot", slot),
            "seed": run.seed, "sampling": info.get("sampling", spec.sampling),
            "request_extra": info.get("request_extra", spec.request_extra),
            "temperature_sent": "temperature" in spec.sampling,
            "ending": ending, "last_turn_no_tool_call": bool(result and result.last_turn_no_tool_call),
            "outputs_valid": valid, "outputs_reason": why, "finished": finished,
            **trace_volume,         # trace_used_bytes, trace_size_bytes (None with trace_usage_reason where not known, never 0): science #34, 18:31Z
            "bytes_into_context": sum(t.bytes_into_context for t in turns),
            # H2's bytes (science's ruling, 2 Nov). None when not known, never 0: counted per option and model, out of the mean, and no retry
            "bytes_between_sites": byte_counts.get("between_sites_rx"), "bytes_registered_counter": byte_counts.get("registered_rx"), "byte_counters": byte_counts,
            "chars_into_context": sum(t.chars_into_context for t in turns),
            "bytes_into_context_method": "exact UTF-8 bytes (and characters) of every tool result as delivered after capping; model-independent",
            "ncio_lock_wait_s": ncio_lock_wait_s,
            "onedata_slot": ({k: onedata_slot[k] for k in ("slot", "user_id", "start", "end")} if onedata_slot else None),
            "onedata_slot_wait_s": slot_wait_s if onedata_slot else None,
            "tokens_into_context": None if tok_source == "unavailable" else sum(t.tokens_into_context for t in turns),
            "tokens_into_context_source": tok_source, "tokens_into_context_reason": tok_reason,
            "input_tokens": sum(t.input_tokens for t in turns), "output_tokens": sum(t.output_tokens for t in turns),
            # input_tokens is the whole prompt; for Claude with caching it is the sum of these three parts
            "uncached_input_tokens": (None if all(t.uncached_input_tokens is None for t in turns)
                                      else sum(t.uncached_input_tokens or 0 for t in turns)),
            "cache_creation_input_tokens": sum(t.cache_creation_input_tokens for t in turns),
            "cache_read_input_tokens": sum(t.cache_read_input_tokens for t in turns),
            "prompt_cache": info.get("prompt_cache"),
            "tool_calls": sum(len(t.tool_calls) for t in turns),
            "validator": "icsa.scoring.report.parse_run_output (the frozen parser, #13)",
            "stop_reasons": result.stop_reasons if result else [], "final_text": result.final_text if result else "",
            "limits": dataclasses.asdict(cfg.limits), "config_status": cfg.status, "model_status": spec.status,
            "prompt_draft_fallback": ctx.texts.draft_fallback, "prompt_source": ctx.texts.source,
            "harness_dirty": dirty, "setup_error": info.get("setup_error"), "cleanup_errors": cleanup_errors,
            "endpoint_retries": info.get("retries", 0),
            "base_repo": BASE_REPO, "base_commit": BASE_COMMIT,
        },
    )
    (run_dir / "run_record.json").write_text(rec.to_json())
    return rec
