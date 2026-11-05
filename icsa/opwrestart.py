"""The op_worker restart log (science, #34, 3 Nov 00:24Z, the operator's ruling): op_worker may be restarted as often as needed on site_g and site_f, and a
restart must not read as a settings change. Two things keep that honest:

* the settings hash leaves out what a restart changes (the pod's restart count and start times; icsa.frsettings.HASH_EXCLUDE), and
* this log, one JSON object per line, holds every restart with its times and the pod identity before and after. A pod identity that is not the
  one the log last accepted is an UNPLANNED restart: dispatch stops, as it did when the identity was in the hash.

Entry kinds, per host ("site_g", "site_f"), in the order `python -m icsa.campaign opw-restart` writes them:

    baseline   the identity accepted at the freeze, written once per host: the reference every later reading is compared with (a later one is not
               honoured; the reference moves only by an `end` or an `accept`)
    begin      dispatch pauses for all options; nothing starts from here until `end`
    stop       the restart command is about to run: runs in flight from here are lost (infrastructure failures, retried in every option alike)
    up         op_worker answers again, with the new identity
    end        the checks passed (warm passes, memory plateau, read check within 20% of its reference): the new identity is accepted and dispatch resumes;
               it is honoured only after its own `begin` and `stop` (an `up` may sit between them)
    abort      the command failed part-way: dispatch stays held until an operator writes `accept`
    accept     an operator's word that the identity now seen is the intended one (after an abort, or a restart done by hand)

A `begin` with no later `end`, `abort` or `accept` is a restart in progress. An identity needs a readable process start: a restart inside the pod
moves only that, so a reading or a baseline without it could not see one and reads as a mismatch. Nothing here touches site_g: it reads and appends a file.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

DEFAULT_LOG = "/mnt/volume2/icsa-2027/site_g_restart_log.jsonl"
KINDS = ("baseline", "begin", "stop", "up", "end", "abort", "accept")
CLOSING = ("end", "abort", "accept")              # these close a restart in progress (abort closes it but keeps dispatch held: see in_progress())

# What a restart changes in the settings command's op_worker_pod object (the real names, from the 2 Nov 16:51Z reading in site_g-config, and the
# older stand-in names), by the identity field they feed. rss_mb is memory, reported apart.
POD_IDENTITY_KEYS = {"restarts": ("restarts", "restart_count"), "pod_started": ("started", "started_at"),
                     "process_started": ("op_worker_process_started",)}
POD_VOLATILE = tuple(sorted({k for ks in POD_IDENTITY_KEYS.values() for k in ks} | {"rss_mb"}))


def identity(fields: dict[str, Any]) -> dict[str, Any]:
    """The op_worker pod's restart identity from the settings command's fields: restart count, pod start, process start (any may be None).
    A restart inside the container (`/etc/init.d/op_worker restart`) moves only the process start; a pod restart moves all three."""
    pod = fields.get("op_worker_pod") if isinstance(fields.get("op_worker_pod"), dict) else {}
    out: dict[str, Any] = {}
    for name, keys in POD_IDENTITY_KEYS.items():
        out[name] = next((pod[k] for k in keys if k in pod), None)
    return out


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def read_log(path: str | Path) -> list[dict[str, Any]]:
    """Every entry in file order. ValueError (the reason only) if the file is missing, unreadable or any line is not a JSON object with a known kind."""
    try:
        text = Path(path).read_text()
    except OSError as e:
        raise ValueError(f"the restart log cannot be read ({type(e).__name__})") from None
    out: list[dict[str, Any]] = []
    prev = ""
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except ValueError:
            raise ValueError(f"the restart log has a line that is not JSON (line {n})") from None
        if not isinstance(e, dict) or e.get("kind") not in KINDS or not isinstance(e.get("host"), str):
            raise ValueError(f"the restart log has an entry with no known kind or host (line {n})")
        if e.get("prev", "") != prev:        # each entry carries the sha256 of the line before it: an edited, removed or reordered line breaks the chain
            raise ValueError(f"the restart log's chain is broken at line {n}: an earlier entry was changed, removed or reordered")
        prev = hashlib.sha256(line.encode()).hexdigest()
        out.append(e)
    return out


def append(path: str | Path, entry: dict[str, Any]) -> dict[str, Any]:
    """Append one entry (time added), flushed and fsynced under an exclusive lock, so the scheduler never reads half a line and a crash loses
    at most the entry being written. Returns the entry as written."""
    if entry.get("kind") not in KINDS or not isinstance(entry.get("host"), str):
        raise ValueError(f"not a restart-log entry: {entry!r}")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(p, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o664)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        with open(fd, "rb", closefd=False) as rf:
            lines = [x for x in rf.read().decode().splitlines() if x.strip()]
        e = {"utc": utc_now(), **entry, "prev": hashlib.sha256(lines[-1].encode()).hexdigest() if lines else ""}
        os.write(fd, (json.dumps(e, sort_keys=True) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    return e


def _host(entries: Iterable[dict[str, Any]], host: str) -> list[dict[str, Any]]:
    return [e for e in entries if e["host"] == host]


def has_process_start(ident: Any) -> bool:
    """Whether an identity carries a readable process start: a restart inside the pod moves only that field, so without it none could be seen."""
    v = ident.get("process_started") if isinstance(ident, dict) else None
    return v is not None and not (isinstance(v, str) and not v.strip())


def accepted(entries: list[dict[str, Any]], host: str) -> dict[str, Any] | None:
    """The identity the log last accepted for the host, or None. Only the transitions the command writes move it: the host's first `baseline`, an
    `end` that follows its own `begin` and `stop` (an `up` may sit between), and an operator's `accept`. A later `baseline`, or an `end` with no
    `begin` and `stop` before it, is not honoured, so the identity it names reads as unplanned (dispatch stops) until someone `accept`s it."""
    acc: dict[str, Any] | None = None
    since: list[str] = []         # the kinds written since the last begin, end, abort or accept
    for e in _host(entries, host):
        k = e["kind"]
        if k == "accept" or (k == "baseline" and acc is None):
            acc, since = e.get("identity"), []
        elif k == "begin":
            since = ["begin"]
        elif k in ("stop", "up"):
            since.append(k)
        elif k in ("end", "abort"):
            if k == "end" and since[:2] == ["begin", "stop"]:
                acc = e.get("identity")
            since = []
    return acc


def in_progress(entries: list[dict[str, Any]], host: str) -> str | None:
    """Why dispatch is held by this host's last restart, or None. A `begin` not closed by end/abort/accept is a restart under way;
    an `abort` holds until an operator accepts (the op_worker may be in any state)."""
    last_begin = last_close = -1
    for i, e in enumerate(_host(entries, host)):
        if e["kind"] == "begin":
            last_begin = i
        elif e["kind"] in CLOSING:
            last_close = i
    hs = _host(entries, host)
    if last_begin > last_close:
        return f"an op_worker restart on {host} is under way (begun {hs[last_begin]['utc']})"
    if hs and hs[-1]["kind"] == "abort":
        return f"the op_worker restart on {host} aborted at {hs[-1]['utc']}: {hs[-1].get('why', '')}; an operator must accept the state"
    return None


def completed(entries: list[dict[str, Any]], host: str | None = None) -> int:
    """How many restarts have finished (`end` entries); the number stamped on a run that starts after the last of them."""
    return sum(1 for e in entries if e["kind"] == "end" and (host is None or e["host"] == host))


def windows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each restart as {host, no, stop_utc, end_utc}: from the `stop` entry (the command was about to run; runs in flight from here are lost) to
    its `end` (or None while open or aborted). A restart with no `stop` entry (aborted before it ran) has no window."""
    out: list[dict[str, Any]] = []
    cur: dict[str, dict[str, Any]] = {}
    n: dict[str, int] = {}
    for e in entries:
        h = e["host"]
        if e["kind"] == "begin":
            cur[h] = {"host": h, "no": n.get(h, 0) + 1, "stop_utc": None, "end_utc": None}
        elif e["kind"] == "stop" and h in cur:
            cur[h]["stop_utc"] = e["utc"]
            out.append(cur[h])
        elif e["kind"] in ("end", "abort", "accept") and h in cur:
            if e["kind"] == "end":
                cur[h]["end_utc"] = e["utc"]
                n[h] = cur[h]["no"]
            cur.pop(h)
    return out


def overlapping(entries: list[dict[str, Any]], start_utc: str, end_utc: str) -> list[dict[str, Any]]:
    """The restart windows that a run (or a curve level, or a baseline) from start_utc to end_utc overlaps. An open window (no end yet) reaches
    to now. Times are the ISO strings both sides write, compared as UTC instants."""
    def t(s: str) -> dt.datetime:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    a, b = t(start_utc), t(end_utc)
    hit = []
    for w in windows(entries):
        ws = t(w["stop_utc"])
        we = t(w["end_utc"]) if w["end_utc"] else dt.datetime.max.replace(tzinfo=dt.timezone.utc)
        if ws <= b and a <= we:
            hit.append(w)
    return hit


def state(entries: list[dict[str, Any]] | None, host: str, current: dict[str, Any]) -> tuple[str, str | None]:
    """(state, why) of the host's op_worker against the log, given the identity just read:
        ok        the identity is the accepted one and no restart is under way
        restart   a restart is under way or aborted: dispatch holds, whatever the identity shows
        unplanned the identity differs from the accepted one and no restart of ours explains it: dispatch STOPS
        unknown   the log is missing or has no accepted identity for the host, or the identity could not be read: dispatch HOLDS
    """
    if entries is None:
        return "unknown", "no restart log"
    busy = in_progress(entries, host)
    if busy:
        return "restart", busy
    acc = accepted(entries, host)
    if not isinstance(acc, dict):
        return "unknown", f"the restart log holds no accepted identity for {host} (write a baseline)"
    if all(v is None for v in current.values()):
        return "unknown", "the settings command printed no op_worker pod identity"
    if current != acc:
        diff = ", ".join(f"{k} {acc.get(k)} -> {current.get(k)}" for k in sorted(set(acc) | set(current)) if acc.get(k) != current.get(k))
        return "unplanned", f"op_worker on {host} restarted without the log: {diff}"
    if not has_process_start(current):      # equal to a baseline that has none: a restart inside the pod would still match, so this is a mismatch
        return "unplanned", f"op_worker on {host}: the identity has no readable process start, so a restart inside the pod could not show; dispatch stops"
    return "ok", None


ENV_LOG = "ICSA_SITE_G_RESTART_LOG"      # the scripted runs' restart log (icsa.frsettings.ENV_RESTART_LOG is the same name); the timed commands refuse to start without it


def cut_by_restart(start_epoch: float, end_epoch: float | None = None, path: str | Path | None = None) -> str | None:
    """Timed work (a curve level, a baseline) from start to end (epoch seconds; end = now): why a restart cut it, or None. A level or baseline
    cut by an op_worker restart is redone whole (science, #34, 3 Nov 00:24Z), never recorded as a pass or a fail. The log is the env's
    ICSA_SITE_G_RESTART_LOG, or `path`; none configured: None (not checked; the baseline, the curves and the preflight refuse to start without it, see
    icsa.frsettings.check_from_env and require_restart_log). A configured log that cannot be read raises ValueError, because an
    unreadable log cannot show that nothing cut the work."""
    import time
    p = path or os.environ.get(ENV_LOG)
    if not p:
        return None
    iso = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")      # noqa: E731
    hit = overlapping(read_log(p), iso(start_epoch), iso(time.time() if end_epoch is None else end_epoch))
    if not hit:
        return None
    return "cut by op_worker restart " + ", ".join(f"#{w['no']} on {w['host']} (stop {w['stop_utc']}, end {w['end_utc'] or 'not yet'})" for w in hit)


def lost_by_cell(store) -> dict[str, dict[str, int]]:
    """Per option x layout x model (key "option/layout/model"): the attempts lost to op_worker restarts, and how many of those runs are done now, pending
    again, or out of attempts (infra_exhausted). The restarts themselves are the log's windows; a run that started after restart N carries
    opw_restart_no=N in its record. Every option's runs are counted alike: the same rule applied to all (science, #34, 3 Nov ruling, item 4)."""
    out: dict[str, dict[str, int]] = {}
    seen: set[str] = set()
    for r in store.q("SELECT a.run_key, a.id, r.option, r.layout, r.model, r.status FROM attempts a JOIN runs r ON r.run_key=a.run_key "
                     "WHERE a.infra_kind='op_worker_restart' ORDER BY a.id"):
        cell = out.setdefault(f"{r['option']}/{r['layout']}/{r['model']}", {"lost_attempts": 0, "runs": 0, "done": 0, "pending": 0, "infra_exhausted": 0})
        cell["lost_attempts"] += 1
        if r["run_key"] not in seen:
            seen.add(r["run_key"])
            cell["runs"] += 1
            if r["status"] in ("done", "pending", "infra_exhausted"):
                cell[r["status"]] += 1
    return out
