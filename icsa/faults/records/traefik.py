"""Parser for a Traefik JSON access log that keeps the Range header.

Configuration (day0/traefik-accesslog/accesslog.flags on the 10c lane): `--accesslog.format=json`,
`fields.defaultmode=keep`, `fields.headers.names.Range=keep`. Fields used: RequestMethod,
RequestPath, DownstreamStatus, DownstreamContentSize, ClientHost, StartUTC, request_Range, request_X-Icsa-Run,
request_User-Agent.

Checked against REAL lines of site_g's Traefik v3.5.3 (`/data/access.log`, 1 Nov 2026 21:20-21:21Z, own run keys only):
the field names are as above; `StartUTC` is RFC 3339 with nanoseconds and `Z`; `Duration` is an integer in
nanoseconds (not used here); the run header is logged as `request_X-Icsa-Run` (matched case-insensitively); a content
read is `GET /api/v3/oneprovider/data/<id>/content` with `request_Range` (206) or without it (200, D's download); the
client also sends `POST .../lookup-file-id/<space>/<path>` and `GET .../data/<id>` (attributes), both OTHER here.
`ClientHost` is the cluster's NAT address on every line, so it never attributes a line. M's oneclient does not pass
the gate: its only Traefik lines are `GET /clproto` websocket upgrades with no run key and no file.

A line that is not JSON or lacks RequestPath/RequestMethod is counted in `n_bad`; above `max_bad` the parse raises
`RecordFormatError` instead of returning fewer events.

The REST path names a file by ID (`.../data/<id>/content`), not by name: the manifest maps IDs to
days. Only GET content requests count as reads; `/children` is a listing; everything else is other.
"""
from __future__ import annotations

import datetime as dt
import json
import re

from .base import AccessEvent, Kind, ParseResult, Record, RecordFormatError, register

_CONTENT = re.compile(r"/data/([^/?]+)/content/?$")
_CHILDREN = re.compile(r"/data/([^/?]+)/children/?$")
MAX_BAD = 2


def _ts(s: str | None) -> float | None:
    if not s:
        return None
    try:
        t = re.sub(r"(\.\d{6})\d+", r"\1", s.replace("Z", "+00:00"))   # ns -> us
        d = dt.datetime.fromisoformat(t)
    except ValueError:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)).timestamp()


RUN_HEADER = "X-ICSA-Run"    # needs `--accesslog.fields.headers.names.X-ICSA-Run=keep`


def _run_key(d: dict) -> str | None:
    """The per-run header, whatever case Traefik logs its name in (`request_<name>`)."""
    want = ("request_" + RUN_HEADER).lower()
    for k, v in d.items():
        if k.lower() == want and isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _user_agent(d: dict) -> str | None:
    for k, v in d.items():
        if k.lower() == "request_user-agent" and isinstance(v, str):
            return v
    return None


@register(Record.TRAEFIK)
def parse_traefik(text: str, max_bad: int = MAX_BAD, **_) -> ParseResult:
    events, n_lines, bad, untimed = [], 0, 0, 0
    bad_samples: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        n_lines += 1
        try:
            d = json.loads(line)
            path = d["RequestPath"].split("?", 1)[0]      # a query string never hides a content read
            method = d["RequestMethod"]
        except (ValueError, KeyError, TypeError, AttributeError):
            bad += 1
            if len(bad_samples) < 2:
                bad_samples.append(line[:120])
            continue
        ts = _ts(d.get("StartUTC") or d.get("time"))
        if ts is None:
            untimed += 1
        m = _CONTENT.search(path)
        if m and method == "GET":
            kind, target = Kind.READ, m.group(1)
        elif _CHILDREN.search(path):
            kind, target = Kind.LIST, _CHILDREN.search(path).group(1)
        else:
            kind, target = Kind.OTHER, None
        events.append(AccessEvent(
            ts=ts, kind=kind, target=target, status=d.get("DownstreamStatus"),
            range_header=d.get("request_Range"), content_size=d.get("DownstreamContentSize"),
            client=d.get("ClientHost"), record=Record.TRAEFIK, raw=line, run_key=_run_key(d),
            user_agent=_user_agent(d)))
    if bad > max_bad:
        raise RecordFormatError(f"traefik log: {bad} of {n_lines} lines are not access-log JSON with RequestPath and "
                                f"RequestMethod (more than {max_bad}); first: {bad_samples}")
    return ParseResult(events, n_lines, bad, untimed)
