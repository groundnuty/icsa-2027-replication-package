"""The equality check of the knowledge plane across options (#6). NOT a configuration comparison.

For each option (T, T-unpaginated, D, M) it starts that option's sandbox (`SandboxFactory`), starts the knowledge
plane exactly as a run does (`KnowledgePlane` from the same factory), and sends every probe through the harness's own
`ToolBox` (the run loop's dispatch and output cap), so the response is the one the agent would receive in that option's
run. It then diffs, across options, (1) the tool definitions the model is handed and (2) the response text of every
probe, including the calls to tools that must be disabled. A run of T is repeated once as a control: if the same
option does not reproduce its own responses, the probe is volatile and the check says so instead of claiming a diff.

The sandbox is also exercised (one cell prints which interpreter it is) and its metadata recorded, so a report shows
that the responses were taken while that option's sandbox was up. The knowledge server itself is a stdio child of
the harness, outside the sandbox; the sandbox cannot reach it, and cannot change what it returns. That is a property
the report states and the probes can show only for the harness-side path: see protocol/knowledge/README.md.
"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable, Sequence

from icsa.harness.adapters import ToolCall
from icsa.harness.config import Limits
from icsa.harness.knowledge import KnowledgePlane
from icsa.harness.loop import ToolBox
from icsa.harness.sandbox_api import SandboxFactory
from icsa.records import Layout, Option

from . import extent_meta, pin

OPTIONS = (Option.T, Option.T_UNPAGINATED, Option.D, Option.M)
DISABLED_PROBES = ("list_user_spaces", "list_space_providers", "list_children", "list_files_recursively", "query_by_metadata", "download_file", "grep_file_content")


def probes(space_name: str, layout: Layout) -> list[tuple[str, dict]]:
    """(tool, arguments). The same list for every option; only the layout changes the paths."""
    root = f"/{space_name}/{extent_meta.S1_DIRNAME}" if layout is Layout.S1 else f"/{space_name}/{extent_meta.S2_DIRNAME}/sst_s2.nc"
    live = [
        ("get_file_attributes", {"file_id_or_path": root, "attributes": ["name", "type", "hasJsonMetadata"]}),
        ("get_file_metadata", {"file_id_or_path": root, "metadata_types": ["json"]}),
    ]
    dead = [("list_user_spaces", {}), ("list_space_providers", {"space_id": space_name}),
            ("list_children", {"file_id_or_path": root}), ("list_files_recursively", {"path": root}),
            ("query_by_metadata", {"space": space_name, "predicate": "variable=*"}),
            ("download_file", {"file_id_or_path": root}), ("grep_file_content", {"file_id_or_path": root, "pattern": "x"})]
    return live + dead


@dataclasses.dataclass
class OptionObservation:
    option: str
    tool_definitions_sha256: str
    tool_definitions: list[dict]
    responses: dict[str, dict]            # probe key -> {"text", "is_error", "sha256"}
    sandbox_metadata: dict
    sandbox_cell: dict


def _key(tool: str, args: dict) -> str:
    return f"{tool} {json.dumps(args, sort_keys=True)}"


def _sha(x: Any) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


async def observe(option: Option, layout: Layout, space_name: str, sandbox_factory: SandboxFactory,
                  plane_factory: Callable[[], KnowledgePlane], data_config: dict, limits: Limits,
                  run_key: str) -> OptionObservation:
    sb = await asyncio.to_thread(sandbox_factory, run_key, option, layout, data_config)
    try:
        cell = await asyncio.to_thread(sb.exec, "import sys; print('sandbox-up', sys.version_info[:2])", 120.0)
        async with plane_factory() as kp:
            box = ToolBox(sb, limits, kp)
            defs = [d for d in box.definitions() if d["name"] != "python"]
            responses = {}
            for i, (tool, args) in enumerate(probes(space_name, layout)):
                if tool in DISABLED_PROBES:
                    # straight to the server session: the ToolBox would answer "unknown tool" itself for a name
                    # the plane does not expose, which would hide a server that still offers the tool
                    text, err = await kp.call(tool, args)
                else:
                    res = await box.run(ToolCall(f"eq-{i}", tool, args), time.monotonic() + 120)
                    text, err = res.text, res.is_error
                responses[_key(tool, args)] = {"text": text, "is_error": err, "sha256": _sha(text)}
        return OptionObservation(option.value, _sha(defs), defs, responses,
                                 json.loads(json.dumps(sb.metadata(), default=str)),
                                 {"exit_code": cell.exit_code, "stdout": cell.stdout.strip()})
    finally:
        await asyncio.to_thread(sb.stop)


def compare(obs: Sequence[OptionObservation], control: OptionObservation | None = None) -> dict:
    """Diff every option against the first. `control` is a second observation of the first option."""
    base, diffs = obs[0], []
    for o in obs[1:]:
        if o.tool_definitions != base.tool_definitions:
            diffs.append({"option": o.option, "what": "tool definitions"})
        for k, r in base.responses.items():
            other = o.responses.get(k)
            if other is None or (other["text"], other["is_error"]) != (r["text"], r["is_error"]):
                diffs.append({"option": o.option, "what": "response", "probe": k})
    volatile = []
    if control is not None:
        volatile = [k for k, r in base.responses.items() if (control.responses[k]["text"], control.responses[k]["is_error"]) != (r["text"], r["is_error"])]
    live_ok = all(not r["is_error"] for o in obs for k, r in o.responses.items() if k.split()[0] not in DISABLED_PROBES)
    dead_ok = all(r["is_error"] and "unknown tool" in r["text"].lower() for o in obs for k, r in o.responses.items() if k.split()[0] in DISABLED_PROBES)
    return {"options": [o.option for o in obs], "differences": diffs, "volatile_probes_in_control": volatile,
            "live_probes_succeeded_in_every_option": live_ok, "disabled_tools_refused_in_every_option": dead_ok,
            "identical": not diffs and not volatile and live_ok and dead_ok,
            "tool_definitions_sha256": {o.option: o.tool_definitions_sha256 for o in obs}}


async def run_check(layout: Layout, space_name: str, sandbox_factory: SandboxFactory,
                    plane_factory: Callable[[], KnowledgePlane], data_config_for: Callable[[Option], dict],
                    limits: Limits, out: Path | None = None, options: Sequence[Option] = OPTIONS) -> dict:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    obs = [await observe(o, layout, space_name, sandbox_factory, plane_factory, data_config_for(o), limits,
                         f"kp-eq-{stamp}-{layout.value}-{o.value}") for o in options]
    control = await observe(options[0], layout, space_name, sandbox_factory, plane_factory, data_config_for(options[0]),
                            limits, f"kp-eq-{stamp}-{layout.value}-{options[0].value}-control")
    frozen_sha = json.loads(pin.TOOLS_FILE.read_text())["sha256"]
    report = compare(obs, control)
    report.update({"layout": layout.value, "space": space_name, "utc": stamp,
                   "server_commit": pin.load_pin()["server"]["commit"], "frozen_manifest_sha256": frozen_sha,
                   "observations": [dataclasses.asdict(o) for o in obs]})
    if out:
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str) + "\n")
    return report
