"""Parser for the op-worker file-access audit log, written against REAL lines from site_g (1 Nov 2026, 21:20-21:22Z).

    [2026-11-01 21:20:42.790] request: fuse_request::file_request::open_file_with_extended_info; user: <user id>; file_uuid: <uuid>; share_id: null; path: /<space id>/s1z/sst_19820105.nc

The line format the docs describe (`<date> <time>; request: ...`, no brackets) is NOT what op_worker 25.0 writes;
the parser written for it matched none of the real lines. Facts from the live check (`icsa.faults.live_check`, own slot
users, own space, every line checked against the host's own UTC stamps of the same read):

- The timestamp is UTC, in brackets, with milliseconds. `tz` stays a parameter, default UTC.
- `share_id` was `null` on every line; `path` is `/<space id>/<rel path>`, or `/` (user root), or `null`.
- The request type does NOT tell the client: a REST read (T, D) is logged as `fuse_request::...` too:
  T and D per GET: `fuse_request::resolve_guid_by_relative_path`, `fuse_request::file_request::get_file_attr`,
  `...::open_file_with_extended_info`, `...::synchronize_block`, one `proxyio_request::remote_read`, `...::release`;
  M (oneclient, proxy I/O): `...::get_child_attr`, `...::get_file_location`, `...::open_file`, N x
  `proxyio_request::remote_read` (N grows with the client's read calls, not with the bytes), `...::fsync`,
  `...::release`; a directory listing is `...::get_file_children_attrs`.
  So `remote_read` is not unique to M and `fuse_request` does not mean oneclient: each option is calibrated against
  ITS OWN lines (its own slot users), never against another option's request mix.

A line that does not match is never dropped silently: the count is in `ParseResult.n_bad` and the lines in `bad_lines`, and
above `max_bad` the parse raises `RecordFormatError`, because a format drift would otherwise make every file look unread. The
scorer reads what `salvage` can of each and invalidates any run it may belong to: it may be one of that run's reads.
"""
from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo

from .base import AccessEvent, Kind, ParseResult, Record, RecordFormatError, register

_LINE = re.compile(
    r"^\[(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2}:\d{2}(?:\.\d+)?)\] "
    r"request: (?P<req>[^;]+); user: (?P<user>[^;]*); file_uuid: (?P<uuid>[^;]*); "
    r"share_id: (?P<share>[^;]*); path: (?P<path>.*)$")

_LIST = frozenset({"get_file_children", "get_file_children_attrs"})   # the listing types seen on site_g; nothing guessed
MAX_BAD = 2          # a truncated last line of a live file is tolerated; more is a format problem


def classify_request(req: str) -> Kind:
    """By the request's own name, the same for every option (see the module doc: no client is inferred from it)."""
    tail = req.split(":" ":")[-1].strip()
    if tail == "remote_read":
        return Kind.READ
    if tail.startswith("open_file"):           # open_file, open_file_with_extended_info
        return Kind.OPEN
    if tail == "release":
        return Kind.RELEASE
    if tail in _LIST:
        return Kind.LIST
    return Kind.OTHER                          # attributes, location, sync, fsync, guid resolution, helper setup


def _null(v: str) -> str | None:
    return None if v in ("null", "undefined", "") else v


@register(Record.AUDIT)
def parse_audit(text: str, tz: str = "UTC", max_bad: int = MAX_BAD, **_) -> ParseResult:
    zone = ZoneInfo(tz)
    events, n_lines, bad, untimed = [], 0, 0, 0
    bad_lines: list[str] = []
    bad_samples: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        n_lines += 1
        m = _LINE.match(line.rstrip())
        if not m:
            bad += 1
            if len(bad_samples) < 2:
                bad_samples.append(line[:120])
            if bad <= max_bad:
                bad_lines.append(line)
            continue
        t = m["time"]
        fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in t else "%Y-%m-%d %H:%M:%S"
        try:
            ts = dt.datetime.strptime(f"{m['date']} {t}", fmt).replace(tzinfo=zone).timestamp()
        except ValueError:
            ts = None
            untimed += 1
        events.append(AccessEvent(
            ts=ts, kind=classify_request(m["req"]), target=_null(m["path"]), alt_target=_null(m["uuid"]),
            client=m["user"], record=Record.AUDIT, raw=line, request=m["req"].strip()))
    if bad > max_bad:
        raise RecordFormatError(f"audit log: {bad} of {n_lines} lines do not match the op_worker 25.0 format "
                                f"(more than {max_bad}); first: {bad_samples}")
    return ParseResult(events, n_lines, bad, untimed, tuple(bad_lines))


_STAMP = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(\.\d+)?\]")
_USER = re.compile(r"user: ([^;]*);")


def salvage(line: str, tz: str = "UTC") -> tuple[float | None, str | None]:
    """(epoch s, user id) of a line the format did not match; None for whichever cannot be read from it."""
    ts = None
    if m := _STAMP.match(line):
        try:
            t = dt.datetime.strptime(m[1], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo(tz)).timestamp()
            ts = t + float(m[2] or 0)
        except ValueError:
            pass
    u = _USER.search(line)
    return ts, u[1] if u else None
