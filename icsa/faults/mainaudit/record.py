"""One main M run's record on the default record (site_g's file-access audit log): its lines, the frozen detector's output on them, and whether the run was observed.

It carries no fault outcome (`fault_injected`, `fault_detected`): `exhibits.fault_injection_adapter` passes such a record by, so a main run never joins the
calibration's table. A missing record is never a detection (amendment 20(d)): a run whose window is not whole, not wholly pulled, crossed by an site_g op_worker
restart (buffered lines may be lost), touched by a malformed line or by another run's lease, or with no line at all is `not_observed`, with the reason. A run
with the mount's lines but no open and no read is `read_nothing`: the record's verdict "read nothing" in the primary (science, #34 07:01Z (2)), with
calibration's rule, which reads it as not observed, kept beside it as a sensitivity (`calibration_rule_class`). A run flagged `orphan_risk` is left out of the
primary and kept for a sensitivity that includes it (07:01Z (3)). The truth the record is scored against is the run's labels (07:01Z (1)), not its own fields.
S2 is never testable on this record (parameters.md: one file, opened either way, no offsets) and is kept as description."""
from __future__ import annotations

import dataclasses
from collections import Counter
from typing import Any, Iterable

from icsa.faults.detector import DetectorSpec, detect
from icsa.faults.records.base import Record
from icsa.records import Layout

from .attribute import Attribution
from .windows import Lease, overlapping

SCHEMA = "m_audit/1"
FLUSH_MARGIN_S = 5.0          # the pull must reach this far past a lease's end before the run is judged (site_g's flush lag is not measured)


@dataclasses.dataclass(frozen=True)
class Capture:
    covered_until: float | None                          # epoch: lines written before this are in the pulled chunks
    covered_from: float | None = None                    # epoch of the ledger's first line: nothing earlier was pulled (Astra, #7)
    mon_span: tuple[float, float] | None = None          # the monitor's first and last sample: an unplanned restart is only seen inside it (Astra, #5)
    gaps: tuple[tuple[float, float | None], ...] = ()    # spans the pull could not read (a rotation, a truncation, an inode change); None: open
    provenance: dict | None = None                       # the ledger rows read, for the record


def _why_not(lease: Lease, at: Attribution, capture: Capture, restarts: list, bad_lines: Iterable[tuple[float | None, str | None]], n_lines: int) -> str | None:
    if lease.end_source == "unknown":
        return "window_end_unknown"
    if lease.end_source == "unverified":                      # no quarantine log for its host: a quarantined end would read as a normal one (Astra, #3)
        return "window_end_unverified"
    if capture.covered_until is None or capture.covered_until < lease.end + FLUSH_MARGIN_S:
        return "capture_incomplete"
    if capture.covered_from is None or capture.covered_from > lease.start - at.eps:      # the pull began after the lease did: its start is missing
        return "capture_starts_after_lease"
    if capture.mon_span is None or not (capture.mon_span[0] <= lease.start and capture.mon_span[1] >= lease.end):
        return "restart_unverified"
    if any(a <= lease.end and lease.start <= (b if b is not None else float("inf")) for a, b in capture.gaps):
        return "capture_gap"
    if restarts:
        return "restart"
    if any(u == lease.user and (t is None or lease.start - at.eps <= t <= lease.end + at.eps) for t, u in bad_lines):
        return "bad_line"                                     # a damaged line of this user with no time could be in any of its leases (Astra, #10)
    if at.ambiguous.get(lease.ident):
        return "ambiguous"
    if not n_lines:
        return "no_lines"
    return None


def build(lease: Lease, at: Attribution, *, capture: Capture, restarts: list[dict], bad_lines: list[tuple[float | None, str | None]], required, manifest,
          condition: str = "cold", flags: Iterable[str] = ()) -> dict[str, Any]:
    evs = sorted(at.per_run.get(lease.ident, []), key=lambda e: e.ts or 0.0)
    hit = overlapping(restarts, lease)
    reason = _why_not(lease, at, capture, hit, bad_lines, len(evs))
    det = None
    if evs and manifest is not None and required is not None:
        out = detect(evs, required, manifest, DetectorSpec(Record.AUDIT))
        det = {"fingerprint": out.fingerprint, "read_days": sorted(out.read), "missing_days": sorted(out.missing), "n_events": out.n_events,
               "n_used": out.n_used, "n_unmapped": out.n_unmapped, "n_unresolved": out.n_unresolved}
    if reason is None and det is None:
        raise ValueError(f"{lease.run_key}: no manifest or required days, so its lines cannot be judged")
    cls = "not_observed" if reason else ("read_nothing" if det["n_used"] == 0 else "observed")
    flags = sorted(set(flags))
    return {
        "schema": SCHEMA, "record_type": "audit", "option": lease.option, "condition": condition,
        "run_key": lease.run_key, "attempt_dir": lease.attempt_dir, "instance": lease.instance, "layout": lease.layout.value, "host": lease.host,
        "window": {"slot": lease.slot, "user_id": lease.user, "lease_start": lease.start, "lease_end": lease.end, "end_source": lease.end_source, "eps_s": at.eps},
        "capture": {"covered_until": capture.covered_until, "gaps": [list(g) for g in capture.gaps], "provenance": capture.provenance},
        "lines": {"n": len(evs), "by_kind": dict(Counter(e.kind.value for e in evs)), "first_ts": evs[0].ts if evs else None, "last_ts": evs[-1].ts if evs else None,
                  "lead_s": (evs[0].ts - lease.start) if evs else None, "tail_s": (lease.end - evs[-1].ts) if evs else None,
                  "n_ambiguous": at.ambiguous.get(lease.ident, 0)},
        "detector": det,
        "restart": hit,
        "verdict": {"class": cls, "reason": reason, "testable": lease.layout is Layout.S1 and cls != "not_observed", "flags": flags,
                    "in_primary": lease.layout is Layout.S1 and cls != "not_observed" and "orphan_risk" not in flags,
                    "calibration_rule_class": "not_observed" if cls == "read_nothing" else cls},
    }
