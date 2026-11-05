"""The sandbox gate's request log (`gate_requests.jsonl`, icsa/sandbox/gate.py), read as the Traefik record it stands in for (amendment 17(c)).

Both record the same things of a REST request: method, path (a file by its id), `Range`, status, and the body bytes of the response. So a gate line becomes the
Traefik record's own event (`Record.TRAEFIK`), and the frozen detector runs on it unchanged, with the same fingerprint. Field by field:

  * `status`: what the provider answered, as Traefik's `DownstreamStatus` is (`upstream_status` on a transfer the gate cut, else `status`); a denial keeps the gate's
    own status, which is not 200 or 206, so it credits nothing, as a request that never reached Traefik credits nothing there.
  * `content_size`: `body_bytes`, what the response handed to the agent's client. Only what is confirmed: a write that failed (`body_bytes_unconfirmed`) is not
    credited. A line without the field, from a gate older than it, is None, unresolved, never credited, so such a log cannot stand in.
  * D: the gate moves the whole file from the provider before the agent sees a byte. Traefik shows that whole file whatever the agent read; the gate shows what
    reached the agent. They can differ only on a download the agent cut, and `gatecheck` names each such case.

Lines that are not requests (`event`: a request the parser refused, a connection error) are not events: a request the parser refused never reached the policy or
the provider. A line that is not JSON counts in `n_bad`; above `max_bad` the parse raises."""
from __future__ import annotations

import json
import re

from .base import AccessEvent, Kind, ParseResult, Record, RecordFormatError

_CONTENT = re.compile(r"/data/([^/?]+)/content/?$")
_CHILDREN = re.compile(r"/data/([^/?]+)/children/?$")
MAX_BAD = 2


def parse_gate(text: str, max_bad: int = MAX_BAD, **_) -> ParseResult:
    events, n_lines, bad, untimed = [], 0, 0, 0
    samples: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        n_lines += 1
        try:
            d = json.loads(line)
            if not isinstance(d, dict):
                raise ValueError("not an object")
        except ValueError:
            bad += 1
            if len(samples) < 2:
                samples.append(line[:120])
            continue
        if "event" in d or "method" not in d or "path" not in d:
            continue
        path, method = str(d["path"]).split("?", 1)[0], d["method"]
        m = _CONTENT.search(path)
        if m and method == "GET":
            kind, target = Kind.READ, m.group(1)
        elif _CHILDREN.search(path):
            kind, target = Kind.LIST, _CHILDREN.search(path).group(1)
        else:
            kind, target = Kind.OTHER, None
        ts = d.get("t")
        if not isinstance(ts, (int, float)):
            ts, untimed = None, untimed + 1
        status = d.get("upstream_status") if d.get("decision") == "allow" and d.get("upstream_status") is not None else d.get("status")
        events.append(AccessEvent(ts=ts, kind=kind, target=target, status=status, range_header=d.get("range"),
                                  content_size=d.get("body_bytes") if isinstance(d.get("body_bytes"), int) else None,
                                  client="gate", record=Record.TRAEFIK, raw=line))
    if bad > max_bad:
        raise RecordFormatError(f"gate log: {bad} of {n_lines} lines are not JSON (more than {max_bad}); first: {samples}")
    return ParseResult(events, n_lines, bad, untimed)


# ---------------------------------------------------------------------------------------------------------------- responses the client did not read to their end
# A response's `body_bytes` is what the gate's socket accepted, and says nothing of what the client read: a client that reads part of a response and closes leaves
# a line that looks complete (the sealed gate validation set). The gate's `conn_close` line (icsa/sandbox/gate.py, `Handler._peer_gone`) says how a connection ended
# after its last response, with the kernel's counters of that moment. `parse_gate` does not read it and credits `body_bytes` as ever; `gate_cuts` lists the responses
# whose connection's close says they were cut, and the scorer leaves them out of recall and precision (science, #34, 15:39Z, 16:00Z).
CLASS_EXTENT_UNKNOWN = "extent_unknown"
CLASS_NOT_CUT = "not_cut"
CLOSE_KINDS = ("eof", "reset", "tls_close", "idle_timeout", "error", "teardown")
TCP_CLOSE = 7          # `tcp_state` of a socket that received a reset


def _count(v) -> int | None:
    """A counter as the gate logged it, or None when it is absent or not a count (a bool is not one)."""
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _outstanding(close: dict) -> bool:
    """Data the client had not acknowledged when the gate looked: `outq_unacked` > 0, or `bytes_acked` < `bytes_sent` - `bytes_retrans`. `bytes_sent` counts a retransmitted
    byte each time it goes out and `bytes_acked` once, so the retransmitted bytes are taken off before the two are compared: a complete read that had a retransmission is not
    outstanding data. If any of the three fields is missing or not a count, `outq_unacked` alone decides; a counter the gate could not read shows nothing."""
    unacked, acked, sent, retrans = (_count(close.get(k)) for k in ("outq_unacked", "bytes_acked", "bytes_sent", "bytes_retrans"))
    if (unacked or 0) > 0:
        return True
    return None not in (acked, sent, retrans) and acked < sent - retrans


def cut_reason(close: dict | None) -> str | None:
    """Why this connection's close says its last response was not read to its end, or None when it says nothing of the kind. `close` is the `conn_close` line, or None
    when the connection has none. The one rule, by `ended`:

      * no close line (None): "no_close_line". The gate died or was killed before it saw the connection end, so nothing shows the client read the response.
      * `reset`: the client's reset arrived before the gate read anything more: "reset". It closed with data unread.
      * `eof`: a FIN. Read to the end if nothing was outstanding when the gate saw it; "unacked" if `outq_unacked` > 0 or `bytes_acked` < `bytes_sent` - `bytes_retrans`
        (`_outstanding`): data still unacknowledged when the client closed cannot have been read. A complete read showed 0 and equal counters before the TLS layer read; the
        retransmitted bytes, which `bytes_sent` counts again, are taken off so that a retransmission is not read as unacknowledged data.
      * `tls_close`: the client sent a TLS close_notify first, so the gate's raw peek saw a record and its TLS read then returned nothing, and the counters were read after
        that read. Less certain than an `eof`: the gate's own TLS reply can make a client that has already closed answer with a reset, and leaves the reply's bytes
        unacknowledged. A reset state (`tcp_state` 7) or anything outstanding is a cut: "reset_state", "unacked".
      * `error`: any other error at the peek. Read as an eof is: outstanding data is "unacked".
      * `teardown`: the gate was stopped with the connection open. Cut if the client's reset had already arrived (`tcp_state` 7: "reset_state") or bytes were outstanding
        then ("unacked"); otherwise not cut, and `gate_endings` still lists it
        with `ended` "teardown" so a count of them can be reported. A teardown with `in_request` (a request read and not yet answered) is not cut: that request shows the
        client read the response before it, and what is outstanding is the answer to it. This is the line to change if science rules that a teardown is always a cut.
      * `idle_timeout`: the client sent nothing for the whole idle time. An idle pooled connection after a complete read shows nothing outstanding: not cut. A client that
        stopped reading mid-body and kept its socket open has a full receive window, which shows as outstanding bytes (`_outstanding`, retransmits subtracted): "unacked".

    A counter the gate could not read (None) shows nothing outstanding: it is not read as a cut. An `ended` that is none of these is a gate this reader does not know:
    ValueError, never read as complete."""
    if close is None:
        return "no_close_line"
    ended = close.get("ended")
    if ended not in CLOSE_KINDS:
        raise ValueError(f"a conn_close line with ended={ended!r}; known: {', '.join(CLOSE_KINDS)}")
    if ended == "reset":
        return "reset"
    if ended == "teardown" and close.get("in_request") is True:
        return None
    if ended == "teardown" and _count(close.get("tcp_state")) == TCP_CLOSE:
        return "reset_state"       # the counters were read after the client's reset had arrived: it closed with data unread, outstanding or not
    if ended == "tls_close" and _count(close.get("tcp_state")) == TCP_CLOSE:
        return "reset_state"
    return "unacked" if _outstanding(close) else None


def gate_endings(text: str) -> list[dict]:
    """How each connection of a gate log ended, by its LAST response: one entry per connection (as the log orders them), for a log that carries `conn` (a line with none, a
    gate that did not write it, is never read, and an old log has no entries). An entry: conn, conn_request, host, method, path, target (as `parse_gate` gives the event),
    range, status (as `parse_gate` gives the event), body_bytes (as logged), ended (the close line's, None when there is none), class (`CLASS_EXTENT_UNKNOWN` or `CLASS_NOT_CUT`),
    reason (`cut_reason`, None when not cut), close (the close line, None when there is none).

    Only the last response of a connection is at stake, and a connection's close line is joined to it on `conn` and `conn_request` == `after_request`. An earlier response
    is never cut here: a later request on the same connection shows the client read its body to the end (HTTP/1.1 clients here, requests and urllib3, do not pipeline).
    For the same reason a close that names a LATER request than the last one logged (the gate was stopped with that request in flight) leaves the last response not cut.
    A line that is not JSON is skipped here: `parse_gate` counts it."""
    closes: dict[tuple, dict] = {}
    last: dict[str, dict] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        if d.get("event") == "conn_close":
            key = (d.get("conn"), d.get("after_request"))
            if key not in closes or (d.get("ended") == "reset" and closes[key].get("ended") != "reset"):
                closes[key] = d            # the first close line of a response, except that a reset wins: the gate's teardown can log a connection while its handler
                                           # wakes for the client's reset, and the reset is what the client did (Codex Astra on gate.py:433)
        elif "event" not in d and "method" in d and "path" in d and d.get("conn") is not None and _count(d.get("conn_request")) is not None:
            if d["conn"] not in last or d["conn_request"] >= last[d["conn"]]["conn_request"]:
                last[d["conn"]] = d
    later = {}                                         # the highest request number any close line names, by connection
    for (conn, after) in closes:
        if _count(after) is not None:
            later[conn] = max(later.get(conn, 0), after)
    out = []
    for conn, d in last.items():
        close = closes.get((conn, d["conn_request"]))
        reason = None if close is None and later.get(conn, 0) > d["conn_request"] else cut_reason(close)
        path = str(d["path"]).split("?", 1)[0]
        content, children = _CONTENT.search(path), _CHILDREN.search(path)
        target = content.group(1) if content and d["method"] == "GET" else (children.group(1) if children else None)
        status = d.get("upstream_status") if d.get("decision") == "allow" and d.get("upstream_status") is not None else d.get("status")
        credits = bool(content) and d["method"] == "GET" and status in CREDIT_STATUSES       # a response the detector can credit bytes for (`parse_gate`: a READ)
        out.append({"conn": conn, "conn_request": d["conn_request"], "host": d.get("host"), "method": d["method"], "path": d["path"], "target": target,
                    "range": d.get("range"), "status": status, "body_bytes": d.get("body_bytes"), "ended": None if close is None else close.get("ended"),
                    "class": CLASS_NOT_CUT if reason is None else CLASS_EXTENT_UNKNOWN, "reason": reason, "close": close, "credits": credits})
    return out


CREDIT_STATUSES = (200, 206)      # the detector's `ok_statuses` (DetectorSpec): only a content GET answered so can credit bytes


def gate_cuts(text: str) -> list[dict]:
    """The responses of a gate log that were cut and could have credited bytes: the entries of `gate_endings` whose class is "extent_unknown" and that are a content GET
    answered 200 or 206 (`credits`). What the client read of one is not known, so it counts neither as read nor as not read; the scorer leaves it out of recall and
    precision. A response that credits nothing (a refusal, an error, a lookup, a listing) is listed by `gate_endings` with its class but is no cut here: in particular the
    gate answers a refusal itself and closes the connection (`_send_json(close=True)`), so such a response has no close line by design. Reasons: reset, unacked,
    reset_state, no_close_line (`cut_reason`). A log with no `conn` has none."""
    return [e for e in gate_endings(text) if e["class"] == CLASS_EXTENT_UNKNOWN and e["credits"]]


CUT_REASONS = ("reset", "unacked", "reset_state", "no_close_line")


def gate_close_summary(text: str) -> dict:
    """How the connections of one run's gate log ended, for the run's report: {"old_format", "connections", "ended", "no_close_line", "cuts"}.

      * `ended`: the number of `conn_close` lines by `ended`, every kind in CLOSE_KINDS present (0 when none); a kind this reader does not know is counted under its own name,
        and `gate_endings` then raises on the connection it closes, so a newer gate is not read as complete.
      * `connections`: the connections of the log (`gate_endings`), and `no_close_line` how many have no close line for their last response (a refusal the gate answered
        and closed itself among them: it credits nothing and is no cut).
      * `cuts`: the responses `gate_cuts` lists (those that could credit bytes), by reason, every reason in CUT_REASONS present.
      * `old_format`: True when the log has no `conn` on any request line and no close line, today's logs: all counts are then zero, and nothing is said of the log's connections."""
    ended = dict.fromkeys(CLOSE_KINDS, 0)
    new = False
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        if d.get("event") == "conn_close":
            new = True
            ended[d.get("ended")] = ended.get(d.get("ended"), 0) + 1
        elif "event" not in d and "method" in d and "path" in d and d.get("conn") is not None:
            new = True
    cuts = dict.fromkeys(CUT_REASONS, 0)
    endings = gate_endings(text) if new else []
    for e in endings:
        if e["reason"] is not None and e["credits"]:          # the cuts `gate_cuts` lists
            cuts[e["reason"]] = cuts.get(e["reason"], 0) + 1
    no_line = sum(1 for e in endings if e["close"] is None)      # every connection whose last response has no close line, a refusal the gate closed itself included
    return {"old_format": not new, "connections": len(endings), "ended": ended, "no_close_line": no_line, "cuts": cuts}
