"""The windows the M audit reader works with: each run's lease of its Onedata slot user, and site_g's op_worker restarts.

The lease, not the run, brackets a run's audit lines. It is taken before the token is minted and released after the sandbox, mount included, is stopped
(`real_sandbox.py` `bind_lease`), and while it is held no other run on that host can hold the same user (a flock per slot key; hosts partition the keys). On
calibration-11's runs every line of a run fell inside its lease (first line 8.6 s or more after its start, last 2.6 s or more before its end), and an M
run's lines go on past its `run_end`. A quarantined lease's `end` is when the quarantine began, not its last read: its window runs to its `free` entry.

Restarts: only site_g's, as M reads site_g alone; `opwrestart.overlapping` has no host filter, so a `site_f` restart would mark M runs. The log's windows (`opwrestart.windows`,
from `stop` to `end`) are extended where it leaves them open: an `abort` after `stop` runs to the next `accept`, and an `accept` with no `stop` (a restart by
hand) runs from its `begin` and is approximate. A restart nobody planned has no entry: site_g's monitor samples op_worker's identity every 10 s, and a change
between two samples is a window too."""
from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Any, Iterable

from icsa import opwrestart
from icsa.records import Layout

QUARANTINE_MATCH_S = 5.0          # a quarantine starts right after the lease's `end` is set (`Lease.quarantine`): within this of it, it is that lease's


class NoLease(ValueError):
    """The run record names no complete lease (no `extras.onedata_slot`, or one with no user, start or end): its lines cannot be found."""


@dataclasses.dataclass(frozen=True)
class Lease:
    run_key: str
    attempt_dir: str
    user: str
    slot: str
    start: float                  # epoch seconds, the run host's clock
    end: float
    layout: Layout
    instance: str | None
    host: str | None
    end_source: str = "lease"     # lease | quarantine_free | unknown (quarantined, never freed on record)
    option: str = "M"

    @property
    def ident(self) -> tuple[str, str]:
        return (self.run_key, self.attempt_dir)


def run_key_of(rec: dict) -> str:
    r = rec["run"]
    return f"{rec['block']}__{r['instance_id']}__{r['option']}__{r['layout']}__{r['model']}__s{r['seed']}"


def lease_from_record(rec: dict, attempt_dir: str, *, host: str | None, quarantines: Iterable[dict] | None = None) -> Lease:
    """The lease of one attempt, from its `run_record.json` (`extras.onedata_slot`, written from `Lease.record()`), extended to its `free` entry when it
    was quarantined (`quarantines.jsonl` of the host it ran on)."""
    sl = (rec.get("extras") or {}).get("onedata_slot") or {}
    if not sl.get("user_id") or sl.get("start") is None or sl.get("end") is None:
        raise NoLease(f"{attempt_dir}: no complete onedata_slot in the run record ({sl!r})"[:300])
    start, end = float(sl["start"]), float(sl["end"])
    if end < start:
        raise NoLease(f"{attempt_dir}: the lease ends before it starts ({start} .. {end})")
    source = "lease"
    evs = list(quarantines or ())
    q = next((e for e in evs if e.get("ev") == "q" and e.get("slot") == sl.get("slot") and abs(float(e.get("start", -1e18)) - end) <= QUARANTINE_MATCH_S), None)
    if q is not None:
        free = next((e for e in evs if e.get("ev") == "free" and e.get("slot") == q["slot"] and e.get("start") == q["start"]), None)
        if free is not None and free.get("end") is not None:
            end, source = max(end, float(free["end"])), "quarantine_free"
        else:
            source = "unknown"
    r = rec["run"]
    return Lease(run_key=run_key_of(rec), attempt_dir=attempt_dir, user=str(sl["user_id"]), slot=str(sl.get("slot")), start=start, end=end,
                 layout=Layout(r["layout"]), instance=r.get("instance_id"), host=host, end_source=source, option=r.get("option", "M"))


def _epoch(utc: str) -> float:
    return dt.datetime.fromisoformat(utc.replace("Z", "+00:00")).timestamp()


def restart_windows(log_entries: list[dict[str, Any]], mon_samples: Iterable[dict[str, Any]], *, host: str = "site_g") -> list[dict[str, Any]]:
    """site_g's op_worker restarts as {source: log|mon, no, from, to (None: open), approximate}, epoch seconds. `log_entries` as `opwrestart.read_log` returns
    them (it checks the hash chain); `mon_samples` the monitor's lines ({ts, opw: {id}}), in any order."""
    mine = [e for e in log_entries if e.get("host") == host]
    out: list[dict[str, Any]] = []
    for w in opwrestart.windows(mine):
        to = _epoch(w["end_utc"]) if w["end_utc"] else None
        if to is None:          # closed by no `end`: an `accept` closes it (Astra, #9); an `abort` runs it to the operator's next `accept`; else it is open
            s = _epoch(w["stop_utc"])
            later = [e for e in mine if _epoch(e["utc"]) > s]
            first_close = next((e for e in later if e["kind"] in ("end", "abort", "accept", "begin")), None)
            if first_close is not None and first_close["kind"] == "accept":
                to = _epoch(first_close["utc"])
            elif first_close is not None and first_close["kind"] == "abort":
                acc = next((e for e in later if e["kind"] == "accept"), None)
                to = _epoch(acc["utc"]) if acc else None
        out.append({"source": "log", "no": w["no"], "from": _epoch(w["stop_utc"]), "to": to, "approximate": False})
    begin, stopped, prev = None, False, None   # a restart by hand: an `accept` with no `stop` since the last `begin` (from it), or with no `begin` at all
    for e in mine:                             # (from the host's previous entry: Astra, #8); an accept after a `stop` is the window above
        if e["kind"] == "begin":
            begin, stopped = e, False
        elif e["kind"] == "stop":
            stopped = True
        elif e["kind"] in ("end", "abort"):
            begin, stopped = (None, False) if e["kind"] == "end" else (begin, stopped)
        elif e["kind"] == "accept":
            if not stopped:
                start = begin["utc"] if begin is not None else (prev["utc"] if prev is not None else None)
                out.append({"source": "log", "no": None, "from": _epoch(start) if start else float("-inf"), "to": _epoch(e["utc"]), "approximate": True})
            begin, stopped = None, False
        prev = e
    prev = None
    for smp in sorted((s for s in mon_samples if (s.get("opw") or {}).get("id")), key=lambda s: float(s["ts"])):
        if prev is not None and smp["opw"]["id"] != prev["opw"]["id"]:
            out.append({"source": "mon", "no": None, "from": float(prev["ts"]), "to": float(smp["ts"]), "approximate": False})
        prev = smp
    return out


def mon_span(mon_samples: Iterable[dict[str, Any]]) -> tuple[float, float] | None:
    """The time the monitor's samples cover (the first and last usable sample): an unplanned restart is only seen inside it (Astra, #5)."""
    ts = [float(s["ts"]) for s in mon_samples if (s.get("opw") or {}).get("id") and s.get("ts") is not None]
    return (min(ts), max(ts)) if ts else None


def overlapping(windows: list[dict[str, Any]], lease: Lease) -> list[dict[str, Any]]:
    """The restart windows a lease overlaps (an open window reaches to now)."""
    return [w for w in windows if w["from"] <= lease.end and lease.start <= (w["to"] if w["to"] is not None else float("inf"))]


# ---------------------------------------------------------------- orphan risk (science, #34 07:01Z (3): out of the primary, counted, in a sensitivity)
# A driver killed during a run (`interrupted` in the store) may leave that sandbox reading with a live token
# while its slot's flock is free, so a later lease of the same user on that host could take in the orphan's lines; the audit line names no session, and the
# store does not say which user the killed attempt held. Every lease of that option on that host is therefore at risk from the killed attempt's start until
# a reap is on record there: each sandbox start runs `netpool.reap_orphans`, recorded as the run's `sandbox.reaped_orphans`. Only a reap that ran (not
# skipped, not failed) and came after the kill was marked (the attempt's end, set when the scheduler found it dead) closes the window. The reap itself comes
# during the reaping run's sandbox start, after its lease began: REAP_BOUND_S bounds that delay (inferred: the start before the agent, not measured), so that
# run's own lease is at risk too.
REAP_BOUND_S = 120.0
KILLED_STATES = ("interrupted",)     # a harness_error leaves its driver alive, which stops its sandbox (runner.py), and main's first 11 failed before any sandbox


def _reaped(ro: Any) -> bool:
    """A reap that ran and left nothing behind: one that `held` a sandbox (its mount could not be inspected or released) closes no window (Astra, #6)."""
    return isinstance(ro, dict) and "skipped" not in ro and "error" not in ro and not ro.get("held")


def killed_attempts(db: Any) -> list[dict[str, Any]]:
    """The store's killed attempts: {host, option, start, end} (epoch). `db` is a path to the mirror's `state.sqlite`, opened read-only."""
    import sqlite3
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = con.execute("select r.option, a.started_utc, a.ended_utc, a.exec_host from attempts a join runs r on r.run_key = a.run_key "
                           f"where a.state in ({','.join('?' * len(KILLED_STATES))})", KILLED_STATES).fetchall()
    finally:
        con.close()
    return [{"host": h or "", "option": o, "start": _epoch(s), "end": _epoch(e) if e else _epoch(s)} for o, s, e, h in rows if s]


def reaps_from_records(attempts: Iterable[tuple[Any, dict]], host_of) -> list[dict[str, Any]]:
    """Each run record whose sandbox start reaped: {host, lease_start, reaped_orphans}."""
    out = []
    for d, rec in attempts:
        ro = (rec.get("sandbox") or {}).get("reaped_orphans")
        start = ((rec.get("extras") or {}).get("onedata_slot") or {}).get("start")
        if _reaped(ro) and start is not None:
            out.append({"host": host_of(d, rec), "lease_start": float(start), "reaped_orphans": ro})
    return out


def orphan_windows(killed: Iterable[dict[str, Any]], reaps: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    reaps = [r for r in reaps if _reaped(r.get("reaped_orphans"))]
    out = []
    for k in killed:
        after = [r["lease_start"] for r in reaps if r["host"] == k["host"] and r["lease_start"] >= k["end"]]
        out.append({"host": k["host"], "option": k["option"], "from": k["start"], "to": (min(after) + REAP_BOUND_S) if after else None})
    return out


def orphan_risk(lease: Lease, windows: Iterable[dict[str, Any]]) -> bool:
    return any(w["host"] == lease.host and w["option"] == lease.option and w["from"] <= lease.end
               and lease.start <= (w["to"] if w["to"] is not None else float("inf")) for w in windows)
