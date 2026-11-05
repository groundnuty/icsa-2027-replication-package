"""The campaign's executor (#16 -> #8): `execute_run(run, attempt, run_dir, slot, cfg, ...)`, synchronous.

The scheduler calls this in worker threads with the campaign config. It builds ONE harness `RunContext` per process,
lazily and under a lock (instances, `HarnessConfig`, adapter factory per slot/backend, knowledge factory, the real
sandbox factory on the pinned image), then runs the async runner with `asyncio.run` in the calling thread.

Nothing here falls back silently: a missing pinned image, a missing knowledge-plane dependency or a prompt slot that
is still a placeholder raises (a harness error, loud and terminal), never a stub. A harness `InfraError` is re-raised
as the campaign's `InfraError` (kind `knowledge` becomes `sandbox`, detail prefixed), which is what the #16 rule keys on.
"""
from __future__ import annotations

import asyncio
import dataclasses
import os
import threading
from pathlib import Path
from typing import Any, Callable

from icsa.campaign.errors import InfraError as CampaignInfraError
from icsa.records import RunId, RunRecord

from .config import HarnessConfig, load_config
from .errors import InfraError
from .prompt import load_prompt_texts
from .runner import RunContext, default_adapter_factory
from .runner import execute_run as _execute_run_async

_LOCK = threading.Lock()
_CTX: dict[tuple, RunContext] = {}
_INFLIGHT: dict[str, int] = {}
_INFLIGHT_LOCK = threading.Lock()


def require_real_prompt_slots(hcfg: HarnessConfig) -> None:
    """A real run never renders a placeholder into a prompt."""
    bad = [k for k, v in {**hcfg.prompt_slots, **{f"{lay}.{k}": v for lay, d in hcfg.prompt_slots_by_layout.items()
                                                  for k, v in d.items()}}.items() if "PLACEHOLDER" in str(v)]
    if bad:
        raise RuntimeError(f"prompt slots still hold placeholders: {sorted(bad)}")


def real_knowledge_factory(hcfg: HarnessConfig, time_cap_s: float) -> Callable:
    """The knowledge-plane factory (#6): a REQUIRED dependency. If it is absent the campaign refuses to run."""
    try:
        from icsa.knowledge.launch import knowledge_factory
    except ImportError as e:
        raise RuntimeError("icsa.knowledge.launch (#6) is required for agent runs and is not available: the campaign "
                           "refuses to run without the knowledge plane (no stub)") from e
    from .real_sandbox import SPACE_ID, mint_token

    from icsa.knowledge.tokencheck import ttl_window

    def token_for_run() -> str:        # per run: scoped, read-only, REST; the plane accepts only a lifetime inside its window
        return mint_token(oneclient=False, interface="rest", time_cap_s=time_cap_s, ttl_s=ttl_window(time_cap_s)[2])[0]
    return knowledge_factory(hcfg.knowledge, token_for_run, space_id=SPACE_ID, time_cap_s=time_cap_s)   # the plane checks against this run cap


def build_context(cfg: Any, *, hcfg: HarnessConfig | None = None, instances: dict | None = None,
                  sandbox_factory: Callable | None = None, knowledge_factory: Callable | None = None,
                  adapter_factory: Callable | None = None, texts=None) -> RunContext:
    hcfg = hcfg or load_config()
    override = getattr(cfg, "time_cap_s", None)
    if override is not None:        # the campaign's cap override applies to execution too, not only to slot admission
        hcfg = dataclasses.replace(hcfg, limits=dataclasses.replace(hcfg.limits, time_cap_s=float(override)))
    # ONE resolved config: the campaign's endpoint settings are the ones the scheduler admits against, so they are the ones the run uses
    # (admission checked server A while the harness file named B). Each run records its base URL (`base_url`), and a test compares them.
    ef, lu = getattr(cfg, "endpoints_file", None), getattr(cfg, "site_b_base_url", None)
    if ef:
        hcfg = dataclasses.replace(hcfg, client=dataclasses.replace(hcfg.client, endpoints_file=os.path.expanduser(str(ef))))
    if lu:
        hcfg = dataclasses.replace(hcfg, site_b={**hcfg.site_b, "base_url": str(lu)})
    require_real_prompt_slots(hcfg)
    cap = hcfg.limits.time_cap_s
    if sandbox_factory is None:
        if not getattr(cfg, "sandbox_image", "") or not getattr(cfg, "pinned_image_id", ""):
            raise RuntimeError("no pinned sandbox image in the campaign config: start the campaign with --sandbox-image "
                               "so it is resolved and pinned by id before any run")
        from .real_sandbox import RealSandboxFactory
        sandbox_factory = RealSandboxFactory(cfg.sandbox_image, cfg.pinned_image_id, cap, sandbox_limits=hcfg.sandbox_limits)
    if instances is None:
        from icsa.instances.load import load_all_instances
        instances = {i.instance_id: i for i in load_all_instances()}
    if knowledge_factory is None:
        knowledge_factory = real_knowledge_factory(hcfg, cap)
    # settings are frozen at registration; before the go decision (pilot, calibration) the pilot is what sets the caps
    adapter_factory = adapter_factory or default_adapter_factory(hcfg, study=study_mode(cfg),
                                                                  check_config=bool(getattr(cfg, "past_pilot", False)))
    return RunContext(cfg=hcfg, texts=texts or load_prompt_texts(), instances=instances, sandbox_factory=sandbox_factory,
                      adapter_factory=adapter_factory, knowledge_factory=knowledge_factory, data_config={})


def study_mode(cfg: Any) -> bool:
    """True when this run must use frozen settings: from the pilot on (`enforce_frozen_settings_from = "pilot"`),
    or only past the pilot (the default)."""
    frm = getattr(cfg, "enforce_frozen_settings_from", "main")
    if frm not in ("pilot", "main"):
        raise ValueError(f"enforce_frozen_settings_from must be 'pilot' or 'main', not {frm!r}")
    return frm == "pilot" or bool(getattr(cfg, "past_pilot", False))


def context(cfg: Any) -> RunContext:
    """The one context per process (per image pin), built lazily and thread-safely."""
    key = (getattr(cfg, "sandbox_image", ""), getattr(cfg, "pinned_image_id", ""), study_mode(cfg),
           bool(getattr(cfg, "past_pilot", False)), getattr(cfg, "time_cap_s", None),
           getattr(cfg, "endpoints_file", None), getattr(cfg, "site_b_base_url", None))
    with _LOCK:
        if key not in _CTX:
            _CTX[key] = build_context(cfg)
        return _CTX[key]


def _to_campaign(e: InfraError) -> CampaignInfraError:
    kind = e.kind if e.kind in ("endpoint", "sandbox", "onedata_health", "key_rejected") else "sandbox"
    detail = e.detail if kind == e.kind else f"{e.kind}: {e.detail}"
    return CampaignInfraError(kind, detail)


def concurrency_unit(ctx: RunContext, model: str, slot: str | None, cfg: Any = None) -> str:
    """The scope of the cap a run counts against, from the slot the campaign chose: the Anthropic API, one site_b
    model (its caps are per model), or the HPC provider (one cap for all site_a stacks)."""
    from icsa.campaign.endpoints import backend_of
    backend = backend_of(slot)
    if backend == "site_b":
        return f"site_b:{ctx.cfg.model(model).key}"
    if backend == "anthropic":     # the campaign's effective caps decide the scope, as its scheduler does
        caps = getattr(cfg, "anthropic_caps", None)
        if caps is not None:
            return f"anthropic:{model}" if model in caps else "anthropic"
    return ctx.cfg.concurrency_unit(ctx.cfg.model(model))      # "anthropic:<model>" (per Claude model) or "site_a"


def execute_run(run: RunId, attempt: int, run_dir: Path, slot: str, cfg: Any,
                provider_cap: int | None = None, *, concurrency_at_start: int | None = None, _ctx: RunContext | None = None) -> RunRecord:
    ctx = _ctx or context(cfg)
    unit = concurrency_unit(ctx, run.model, slot, cfg)
    with _INFLIGHT_LOCK:                      # the runs of this cap's scope executing, this one included
        _INFLIGHT[unit] = _INFLIGHT.get(unit, 0) + 1
        concurrency = _INFLIGHT[unit]
    if concurrency_at_start is not None:      # two hosts: the campaign counts both hosts' runs of this scope; no harness process sees them all
        concurrency = concurrency_at_start
    try:
        return asyncio.run(_execute_run_async(run, attempt, Path(run_dir), slot, ctx,
                                              concurrency_at_start=concurrency, provider_cap=provider_cap))
    except InfraError as e:
        raise _to_campaign(e) from e
    finally:
        with _INFLIGHT_LOCK:
            _INFLIGHT[unit] -= 1
