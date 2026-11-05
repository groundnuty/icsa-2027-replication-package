"""Parser for oneclient `--log-read-write-perf` CSV (read_write_perf-<epoch ms>.csv).

    Time,File,Class,Operation,Offset,Size,Duration [us]
    07:28:18.577948,/<space id>/tput/big_0.bin,ReadCache,prefetch,1000000000,280000,13889
    07:28:18.578091,/<space id>/tput/big_0.bin,FsLogic,read,1000000000,280000,14033

(format as measured in day0/REPORT.md Q1b (c).) `Time` is time of day only: the date comes from the
epoch in the file name, and a drop of more than 12 h in time of day is a midnight rollover (a smaller
step back raises: DST or a clock step cannot be resolved from time of day alone; use UTC). Rows are tagged, not
filtered: FsLogic/read -> READ (a read the client asked for); ReadCache/prefetch -> PREFETCH (data
the client fetched ahead, which the agent may never have read); everything else -> OTHER.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
from zoneinfo import ZoneInfo

from .base import AccessEvent, Kind, ParseResult, Record, RecordFormatError, register

MAX_BAD = 2


def _tod(s: str) -> float:
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


@register(Record.PERF)
def parse_perf(text: str, start_epoch_ms: int, sidecar_id: str, tz: str = "UTC", max_bad: int = MAX_BAD, **_) -> ParseResult:
    zone = ZoneInfo(tz)
    start = dt.datetime.fromtimestamp(start_epoch_ms / 1000, tz=zone)
    day0 = start.replace(hour=0, minute=0, second=0, microsecond=0)
    start_tod = start.hour * 3600 + start.minute * 60 + start.second + start.microsecond / 1e6
    events, n_lines, bad = [], 0, 0
    offset_days, prev, first = 0, None, True
    for row in csv.reader(io.StringIO(text)):
        if not row or row[0].strip() == "Time":
            continue
        n_lines += 1
        try:
            tod = _tod(row[0])
            file_, cls, op = row[1], row[2].strip(), row[3].strip()
            off, size = int(row[4]), int(row[5])
        except (ValueError, IndexError):
            bad += 1
            continue
        if first and tod + 1.0 < start_tod:
            if start_tod - tod < 12 * 3600:
                raise ValueError(f"first row at {tod:.0f}s precedes the file start at {start_tod:.0f}s by under 12 h: "
                                 "a clock step, not midnight; parse with tz='UTC'")
            offset_days = 1            # the file started before midnight and this row is after it
        if prev is not None and tod < prev - 1.0:
            if prev - tod < 12 * 3600:      # a small step back is a clock change (DST, correction), not midnight
                raise ValueError(f"time of day went back from {prev:.0f}s to {tod:.0f}s: not a midnight rollover "
                                 "(DST or clock step); parse with tz='UTC'")
            offset_days += 1
        first, prev = False, tod
        ts = (day0 + dt.timedelta(days=offset_days, seconds=tod)).timestamp()
        kind = Kind.READ if (cls, op) == ("FsLogic", "read") else \
            Kind.PREFETCH if (cls, op) == ("ReadCache", "prefetch") else Kind.OTHER
        events.append(AccessEvent(ts=ts, kind=kind, target=file_, offset=off, length=size,
                                  client=sidecar_id, record=Record.PERF, raw=",".join(row)))
    if bad > max_bad:
        raise RecordFormatError(f"perf CSV: {bad} of {n_lines} rows do not parse (more than {max_bad})")
    return ParseResult(events, n_lines, bad, 0)
