"""A main run's switched-on record (science, #34 07:01Z (6); amendment 35): M's per-read log (oneclient's `--log-read-write-perf` CSV, copied into the run dir
by the sandbox) and the gate log of T, T-unpaginated and D (the stand-in for the Traefik record, amendment 17(c)), each through the frozen detector.

For the gate, amendment 35(c)'s crediting rule too: a response whose connection ended by a reset before the client asked for more is cut, credits nothing and
flags nothing, and a day only cut responses covered is undecided (`cuts.undecided_days`); and, beside it as 35(c) requires, the detector on every response as
the gate logged it (12's full denominators). A gate log with no connection ids is from before the gate marked cuts: amendment 35(e) leaves T's and D's
agent-run measure not available for such runs. A log the sandbox could not stand behind (`gate_transfers.unavailable`: the gate died, restarted, or could not
write) is lost, never read as complete. No log at all is not observed: a missing record is never a detection (amendment 20(d)).

Like the audit record, it carries no fault outcome, and the run's labels are its truth (07:01Z (1)). The verdict's classes follow the audit record's
(record.py): a log with lines but no read is `read_nothing`."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from icsa.faults.cuts import undecided_days
from icsa.faults.detector import DetectorSpec, detect
from icsa.faults.records.base import RecordFormatError, Record
from icsa.faults.records.gate import gate_close_summary, parse_gate
from icsa.faults.records.perf import parse_perf

from .windows import run_key_of

SCHEMA = "switched_on/1"
GATED = ("T", "T-unpaginated", "D")


def _det(out) -> dict:
    return {"fingerprint": out.fingerprint, "read_days": sorted(out.read), "missing_days": sorted(out.missing), "n_events": out.n_events,
            "n_used": out.n_used, "n_unmapped": out.n_unmapped, "n_unresolved": out.n_unresolved}


def _base(run_dir: Path, rec: dict, record_type: str) -> dict:
    r = rec["run"]
    return {"schema": SCHEMA, "record_type": record_type, "run_key": run_key_of(rec), "attempt_dir": run_dir.name, "option": r["option"], "layout": r["layout"],
            "instance": r.get("instance_id"), "detector": None}


def _verdict(out: dict, reason: str | None, n_used: int | None) -> dict:
    cls = "not_observed" if reason else ("read_nothing" if n_used == 0 else "observed")
    out["verdict"] = {"class": cls, "reason": reason, "in_primary": cls != "not_observed", "flags": []}
    return out


def gate_record(run_dir: Path, rec: dict, *, required, manifest) -> dict:
    out = _base(run_dir, rec, "gate")
    p = run_dir / "gate_requests.jsonl"
    if not p.is_file():
        return _verdict(out, "no_log", None)
    lost = ((rec.get("sandbox") or {}).get("gate_transfers") or {}).get("unavailable")
    if lost:
        out["lost"] = lost
        return _verdict(out, "log_lost", None)
    text = p.read_text()
    if gate_close_summary(text)["old_format"]:
        return _verdict(out, "old_gate", None)
    try:
        pr = parse_gate(text)
    except RecordFormatError as e:
        out["error"] = str(e)[:300]
        return _verdict(out, "bad_lines", None)
    if pr.n_bad:                                   # a damaged line could be a read: never scored as if whole (Astra, #11)
        out["n_bad"] = pr.n_bad
        return _verdict(out, "bad_lines", None)
    full = detect(pr.events, required, manifest, DetectorSpec(Record.TRAEFIK))
    u = undecided_days(text, required, manifest)
    out["detector"] = _det(full)
    out["cut_rule"] = {k: u[k] for k in ("missing_complete", "undecided", "decided_missing", "fingerprint", "n_unresolved")} | {"counts": u["counts"]}
    return _verdict(out, None, full.n_used)


def perf_record(run_dir: Path, rec: dict, *, required, manifest) -> dict:
    out = _base(run_dir, rec, "perf")
    files = sorted((run_dir / "oneclient_perf").glob("read_write_perf-*.csv"))
    if not files:
        return _verdict(out, "no_log", None)
    events, n_bad = [], 0
    try:
        for f in files:
            start_ms = int(f.stem.rsplit("-", 1)[1])
            pr = parse_perf(f.read_text(), start_ms, f.name)
            events += pr.events
            n_bad += pr.n_bad
    except (RecordFormatError, ValueError) as e:
        out["error"] = str(e)[:300]
        return _verdict(out, "bad_lines", None)
    if n_bad:                                      # a damaged row could be a read (Astra, #11)
        out["n_bad"] = n_bad
        return _verdict(out, "bad_lines", None)
    o = detect(events, required, manifest, DetectorSpec(Record.PERF))
    out["detector"] = _det(o)
    out["files"] = [f.name for f in files]
    return _verdict(out, None, o.n_used)


def build(run_dir: Path, rec: dict, *, required, manifest) -> dict[str, Any]:
    opt = rec["run"]["option"]
    if opt == "M":
        return perf_record(run_dir, rec, required=required, manifest=manifest)
    if opt in GATED:
        return gate_record(run_dir, rec, required=required, manifest=manifest)
    raise ValueError(f"{opt}: no switched-on record (M+ has none, amendment 30(h))")
