"""Rebuild a RunRecord from the JSON a run directory holds, and join it to the campaign's facts.

The executor (#8) writes `run.json` before the scheduler (#16) knows the block and the attempt; the
scheduler's `_write_meta` merges them only into `run_record.json` (the stub's file) and always writes
`campaign_attempt.json`. So the record alone is not trustworthy for `block`, `attempt` and
`exclude_from_analysis`: the campaign store is (`resolve_record`).
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from icsa.records import Layout, Option, RunId, RunRecord, Termination, Turn

RECORD_FILES = ("run_record.json", "run.json")      # the executor writes run_record.json since the glue branch; run.json is the old name


class PipelineError(Exception):
    """A run the pipeline cannot process; `reason` is a short code, listed in the manifest."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


def record_from_dict(d: dict) -> RunRecord:
    d = dict(d)
    r = d.pop("run")
    run = RunId(r["instance_id"], Option(r["option"]), Layout(r["layout"]), r["model"], int(r["seed"]))
    turn_fields = {f.name for f in dataclasses.fields(Turn)}
    turns = []
    for t in d.pop("turns"):
        extra = set(t) - turn_fields
        if extra:
            raise ValueError(f"unknown turn fields {sorted(extra)}")
        turns.append(Turn(**t))
    d["termination"] = Termination(d["termination"])
    known = {f.name for f in dataclasses.fields(RunRecord)}
    extra = set(d) - known
    if extra:       # a silently dropped field is a silent fallback
        raise ValueError(f"unknown run record fields {sorted(extra)}")
    return RunRecord(run=run, turns=turns, **d)


def read_record(run_dir: Path) -> tuple[RunRecord, dict]:
    """The record and its raw dict, from `run.json` or else `run_record.json`."""
    for name in RECORD_FILES:
        p = run_dir / name
        if p.is_file():
            try:
                raw = json.loads(p.read_text())
                return record_from_dict(raw), raw
            except (ValueError, KeyError, TypeError) as e:
                raise PipelineError("bad_run_record", f"{name}: {type(e).__name__}: {e}"[:300]) from e
    raise PipelineError("no_run_record", f"neither {' nor '.join(RECORD_FILES)} in {run_dir}")


def resolve_record(run_dir: Path, entry: dict, store_row, ) -> tuple[RunRecord, dict]:
    """The analysed attempt's record with the campaign fields set from the store (`entry` is the
    export's `analysed_attempts` row, `store_row` the run's row). Any disagreement is an error."""
    rec, raw = read_record(run_dir)
    if rec.run.key() != entry["key"]:
        raise PipelineError("record_key_mismatch", f"record {rec.run.key()} vs store {entry['key']}")
    if rec.block not in (None, entry["block"]):
        raise PipelineError("campaign_meta_mismatch", f"record block {rec.block!r} vs store {entry['block']!r}")
    if rec.block is not None and rec.attempt != entry["attempt"]:
        raise PipelineError("campaign_meta_mismatch", f"record attempt {rec.attempt} vs store {entry['attempt']}")
    excl = bool(store_row["exclude_from_analysis"])
    meta = run_dir / "campaign_attempt.json"
    if meta.is_file():
        m = json.loads(meta.read_text())
        want = {"run_key": entry["run_key"], "block": entry["block"], "attempt": entry["attempt"],
                "exclude_from_analysis": excl}
        bad = {k: (m.get(k), v) for k, v in want.items() if m.get(k) != v}
        if bad:
            raise PipelineError("campaign_meta_mismatch", f"campaign_attempt.json vs store: {bad}")
        if m.get("infra_failure"):
            raise PipelineError("analysed_attempt_is_infra_failure", str(m.get("infra_reason")))
    if rec.infra_failure:
        raise PipelineError("analysed_attempt_is_infra_failure", str(rec.infra_reason))
    rec.block, rec.attempt, rec.exclude_from_analysis = entry["block"], int(entry["attempt"]), excl
    raw = dict(raw, block=entry["block"], attempt=int(entry["attempt"]), exclude_from_analysis=excl,
               infra_failure=False)
    return rec, raw
