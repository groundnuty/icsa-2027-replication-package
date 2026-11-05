"""Stub run executor and health check, standing in for #8 and #10 until they land.

The stub follows the #8 contract: execute_run(run, attempt, run_dir, slot, config)
returns a RunRecord, or raises InfraError. Behaviour comes from a JSON plan
(path in ICSA_STUB_PLAN or the `plan` argument):
  {"sleep_s": 0.2, "infra": {"<run_key>": {"fail_attempts": 2, "kind": "endpoint"}},
   "log": "<path>"}
A run listed under "infra" raises InfraError on infra attempts 1..fail_attempts
and succeeds after that. The decision depends only on (run_key, attempt), never
on how often the process was killed. Every start and end is appended to "log".
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path
from typing import Any

from icsa.records import RunId, RunRecord, Termination, Turn

from .errors import InfraError


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def make_stub_executor(plan: dict[str, Any] | None = None):
    plan = plan if plan is not None else json.loads(Path(os.environ["ICSA_STUB_PLAN"]).read_text())

    def log(line: str) -> None:
        if plan.get("log"):
            fd = os.open(plan["log"], os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            try:
                os.write(fd, (line + "\n").encode())
            finally:
                os.close(fd)

    def execute_run(run: RunId, attempt: int, run_dir: Path, slot: str, config: Any,
                    provider_cap: int | None = None) -> RunRecord:
        key = run.key()
        run_dir.mkdir(parents=True, exist_ok=True)
        log(f"start {key} a{attempt} pid{os.getpid()}")
        time.sleep(plan.get("sleep_s", 0.0))
        spec = plan.get("infra", {}).get(key)
        fails = bool(spec and attempt <= spec["fail_attempts"])
        if fails and not spec.get("write_record"):
            log(f"infra {key} a{attempt}")
            raise InfraError(spec.get("kind", "endpoint"), f"stub failure on attempt {attempt}")
        t = Turn(0, plan.get("input_tokens", 100), plan.get("output_tokens", 10), [], [], 50, 12)
        rec = RunRecord(
            run=run, started_at=_now(), ended_at=_now(), termination=Termination.REPORT,
            error_type=None, model_api_id="stub", endpoint=slot, model_version=None,
            seed_honoured=False, temperature=0.0, turns=[t], transcript_path="transcript.json",
            code_cells_path="cells.json", output_dir="output", wall_time_s=plan.get("sleep_s", 0.0),
            concurrency_at_start=1, site_id="stub", provider_id="stub", harness_commit="stub",
            sandbox={}, extras={"bytes_between_sites": 1000, "provider_cap": provider_cap})
        tmp = run_dir / "run_record.json.tmp"
        tmp.write_text(rec.to_json())
        os.replace(tmp, run_dir / "run_record.json")
        if fails:  # the executor wrote its record and then failed by infrastructure
            log(f"infra {key} a{attempt}")
            raise InfraError(spec.get("kind", "endpoint"), f"stub failure after writing the record, attempt {attempt}")
        log(f"end {key} a{attempt}")
        return rec

    return execute_run


def stub_health_check() -> tuple[bool, str]:
    return True, "stub: always healthy (the real check comes from the #10 lane)"
