"""One short tool-call round trip against a model (the adapter test). Live calls only on request:

    uv run python -m icsa.harness.roundtrip qwen            # a vLLM model by config key
    uv run python -m icsa.harness.roundtrip sonnet
    uv run python -m icsa.harness.roundtrip qwen site_b    # the site_b backend

The model must call the python tool to print 6*7 and then answer. Uses the stand-in sandbox
(this checks the adapter, not any option). Prints a one-line summary, never a key.
"""
from __future__ import annotations

import asyncio
import dataclasses
import sys
import tempfile
from pathlib import Path

from icsa.records import Layout, Option

from .config import load_config
from .loop import ToolBox, run_agent
from .runner import default_adapter_factory
from .sandbox_api import LocalSubprocessStandIn
from .slots import SlotPool

SYSTEM = "You are a test agent. Use the python tool when asked to compute something, then answer briefly."
USER = "Use the python tool to print the product of 6 and 7, then reply with that number."


async def roundtrip(model_key: str, limits_override: dict | None = None, backend: str = "hpc") -> dict:
    cfg = load_config()
    spec = cfg.model(model_key)
    limits = dataclasses.replace(cfg.limits, **{"max_tool_rounds": 4, **(limits_override or {})})
    cfg = dataclasses.replace(cfg, limits=limits)
    slot = None
    if spec.kind == "openai_compat":
        slot = (f"site_b:{spec.api_id.split('/')[-1]}" if backend == "site_b"
                else SlotPool.from_file(cfg.client.endpoints_file).acquire(spec.endpoint_name).slot)
    adapter = default_adapter_factory(cfg, study=False)(spec, 1, slot)
    sb = LocalSubprocessStandIn(Path(tempfile.mkdtemp(prefix="rt-")))
    try:
        r = await run_agent(adapter, ToolBox(sb, limits), SYSTEM, USER, limits)
    finally:
        sb.stop()
        await adapter.aclose()
    return {"model": spec.api_id, "endpoint": adapter.info()["endpoint"], "backend": adapter.info().get("backend"),
            "fingerprints": adapter.info().get("system_fingerprints"), "termination": r.termination.value,
            "error_type": r.error_type, "turns": len(r.turns), "tool_calls": sum(len(t.tool_calls) for t in r.turns),
            "answer_has_42": "42" in r.final_text, "max_tokens_sent": spec.output_tokens(limits.max_output_tokens),
            "stop_reasons": r.stop_reasons, "tokens": [(t.input_tokens, t.output_tokens) for t in r.turns]}


if __name__ == "__main__":
    print(asyncio.run(roundtrip(sys.argv[1], backend=sys.argv[2] if len(sys.argv) > 2 else "hpc")))
