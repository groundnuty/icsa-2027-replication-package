"""Days a cut response leaves undecided (science, #34, 15:39Z and 19:02Z): the scoring rule for gate logs that say how each client connection ended.

A response the client cut (`records/gate.py`, `gate_cuts`: class `extent_unknown`) credits nothing and flags nothing: its `body_bytes` is what the gate's socket accepted, and
says nothing of what the client read. So the frozen detector is run on the responses that were not cut, and a day it then calls missing is one of two kinds:

  * decided: no response that was cut could have covered it. The day is missing, as the detector says, and counts in recall and precision;
  * undecided: a cut response's span (the bytes the gate logged as sent, `served_spans`) overlaps the day's chunk. Had the client read that response to the end, the day might
    have been read; the log cannot say, so the day is out of both recall and precision.

A day that a response read to its end covers is read, whatever a cut response also touched. A cut that sent no byte touches nothing. A log with no `conn` (the old gate's) has no
cuts, and the result is the registered detector's on every day. This module reads the log and the manifest and nothing else; the validation set's scorer
(`gate_validation.py`, `score --rule cut`) and the H3 scorer share it. It changes neither the parser nor the detector."""
from __future__ import annotations

import json

from .detector import DetectorSpec, detect
from .records.base import Kind, Record
from .records.gate import gate_cuts, parse_gate
from .records.ranges import served_spans
from .units import Manifest, Required


def _request_key(raw: str) -> tuple | None:
    """(conn, conn_request) of a request line, as `gate_endings` keys it, or None for a line that has neither (an old gate's)."""
    try:
        d = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    conn, n = d.get("conn"), d.get("conn_request")
    if conn is None or not isinstance(n, int) or isinstance(n, bool):
        return None
    return conn, n


def undecided_days(gate_text: str, required: Required, manifest: Manifest, spec: DetectorSpec = DetectorSpec(Record.TRAEFIK)) -> dict:
    """The detector's missing days with the cut responses left out, split into decided and undecided. A dict, JSON-ready, with every list sorted:

      * `missing_complete`: the days the detector calls missing when it is run on the events that were not cut (`detect(complete, required, manifest, spec)`);
      * `undecided`: those of them that a cut response touched; `decided_missing`: the rest of them;
      * `cuts`: each response of `gate_cuts`, in log order, with conn, conn_request, method, path, target, range, status, body_bytes, ended, reason (as `gate_cuts` gives
        them), `span` (the bytes the gate logged as sent: a list of [start, end), `[]` when none, None when `served_spans` cannot say, or the response is no content read),
        `days` (the required days whose chunk [a, b) the span overlaps) and `undecided` (those of `days` that are undecided);
      * `counts`: events, complete_events, cuts, cuts_touching_days, unresolved_cuts (a content read with no resolvable span, e.g. a multi-range 206: it touches nothing,
        as the detector credits it nothing), unmapped_cuts (a content read of a file the manifest does not know), days_touched, missing_complete, undecided, decided_missing;
      * `fingerprint`, `n_unresolved`: the detector's own, from the run on the events that were not cut.

    A cut is matched to its event by the connection and the request number of the event's own line (`conn`, `conn_request`), never by path or position. A cut with no event, or
    with several that share its connection and request number, is a ValueError: it would stay credited."""
    events = parse_gate(gate_text).events
    index: dict[tuple, list[int]] = {}
    for i, ev in enumerate(events):
        k = _request_key(ev.raw)
        if k is not None:
            index.setdefault(k, []).append(i)
    cut_at: dict[int, dict] = {}
    for c in gate_cuts(gate_text):
        hit = index.get((c["conn"], c["conn_request"]), [])
        if len(hit) != 1:                                   # none: it would stay credited; several: the close line cannot say which, and the others would stay credited
            raise ValueError(f"the cut response {c['conn']}/{c['conn_request']} ({c['method']} {c['path']}) matches no event of the gate log" if not hit else
                             f"{len(hit)} request lines share the connection and request number {c['conn']}/{c['conn_request']} of a cut response: the log cannot be read")
        cut_at[hit[0]] = c
    complete = [ev for i, ev in enumerate(events) if i not in cut_at]
    o = detect(complete, required, manifest, spec)
    days = tuple(required.days)
    touched_by: dict[int, tuple[list | None, list[int]]] = {}
    unresolved = unmapped = 0
    for i in sorted(cut_at):
        ev = events[i]
        span: list | None = None
        hit: list[int] = []
        f = manifest.lookup_id(ev.target) if ev.kind is Kind.READ else None
        if ev.kind is Kind.READ and f is None:
            unmapped += 1
        elif f is not None:
            sp = [] if ev.status not in spec.ok_statuses else served_spans(ev.status, ev.range_header, ev.content_size, f.size)
            if sp is None:
                unresolved += 1
            else:
                span = [[s, e] for s, e in sp]
                for d in days:
                    key, a, b = manifest.units[d]
                    if key == f.key and any(s < b and a < e for s, e in sp):
                        hit.append(d)
        touched_by[i] = (span, hit)
    touched = {d for _, hit in touched_by.values() for d in hit}
    undecided = o.missing & touched
    decided = o.missing - undecided
    out_cuts = []
    for i in sorted(cut_at):
        c, (span, hit) = cut_at[i], touched_by[i]
        out_cuts.append({"conn": c["conn"], "conn_request": c["conn_request"], "method": c["method"], "path": c["path"], "target": c["target"], "range": c["range"],
                         "status": c["status"], "body_bytes": c["body_bytes"], "ended": c["ended"], "reason": c["reason"], "span": span, "days": hit,
                         "undecided": sorted(set(hit) & undecided)})
    return {"missing_complete": sorted(o.missing), "undecided": sorted(undecided), "decided_missing": sorted(decided), "cuts": out_cuts,
            "counts": {"events": len(events), "complete_events": len(complete), "cuts": len(out_cuts), "cuts_touching_days": sum(1 for c in out_cuts if c["days"]),
                       "unresolved_cuts": unresolved, "unmapped_cuts": unmapped, "days_touched": len(touched), "missing_complete": len(o.missing),
                       "undecided": len(undecided), "decided_missing": len(decided)},
            "fingerprint": o.fingerprint, "n_unresolved": o.n_unresolved}
