"""The M audit reader's commands. Everything that reads site_g goes through `day0/scripts/dsk.sh` (`remote.DskRemote`): read-only, byte-bounded, under `nice` and
`ionice` inside the pod, filtered to the slot users there and gzipped on the dsk host before ssh. Run by the lead, not by a lane (science, #34 07:01Z).

    python -m icsa.faults.mainaudit preflight --out DIR [--wait-s 60] [--dry-run]
        stat x2 (wait-s apart), the log dir's listing (rotated siblings), the tools there, one timed 4 KB read mid-file and one timed 100 MB read at EOF.
        Writes DIR/preflight.json and DIR/commands.jsonl; exit 0 when the backfill may run, 3 when it must not (the reasons are in the file).
    python -m icsa.faults.mainaudit backfill --store DIR --since 2026-11-04T00:33:45Z [--max-bytes N] [--dry-run]
        from the line at `since` (time bisection, 4 KB probes) to the EOF seen at the start, in pulls of at most max-bytes, slot users of T, T-unpaginated, D, M.
    python -m icsa.faults.mainaudit pull --store DIR [--max-bytes N]       one incremental pull from the ledger's offset (the 15-min loop calls this)
    python -m icsa.faults.mainaudit status --store DIR
    python -m icsa.faults.mainaudit pin                                    the sha256 that freezes the measure's code (measure.pin_hash: its own import walk)
    python -m icsa.faults.mainaudit measure --pin FILE --scored scored_rows.jsonl --platform platform_rows.jsonl --out DIR [--day-truth DIR]
        H3's agent-run measure: counts.json, self_report.json, record.json and record.csv in DIR, no value printed; refuses (exit 3) unless the code hashes to the pin, checked before
        any input is read; any other error exits 4 with its detail in DIR/measure.error.txt (0600) and only its type and that path on the terminal. --day-truth (daytruth.py's
        output) enables the stricter readings (i) and (ii)

The store (default /mnt/volume2/icsa-2027/m-audit): ledger.jsonl, chunks/, windows.jsonl (each remote read's start and end, so any probe can be read
against it), preflight/. `extract` (records per run) is wired separately."""
from __future__ import annotations

import argparse
import os
import datetime as dt
import json
import shlex
import sys
import time
from pathlib import Path
from typing import Callable, Iterable

from icsa.faults.matcher import load_slot_map

REPO = Path(__file__).resolve().parents[3]
STORE = Path("/mnt/volume2/icsa-2027/m-audit")
OPTIONS = ("T", "T-unpaginated", "D", "M")         # science, #34 07:01Z (5): T and D get the same reader
MiB = 2 ** 20
PROBE_BIG = 100 * MiB
NEEDED_POD = ("dd", "grep", "stat", "ls", "sh", "nice", "ionice")    # nice and ionice: science, #34 07:01Z (4); without one the pre-flight says no
NEEDED_DSK = ("gzip",)


def slot_users(options: Iterable[str] = OPTIONS, path: Path | None = None) -> list[str]:
    users = sorted({s.user for s in load_slot_map(path or REPO / "config" / "slot_map.json").values() if s.option in set(options)})
    if not users:
        raise SystemExit("no slot users for " + ",".join(options))
    return users


def _utc(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _epoch(s: str) -> float:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


class Windows:
    """windows.jsonl: one line per remote read, its start and end (science, 07:01Z (4): each pull's window logged)."""

    def __init__(self, store: Path):
        self.path = store / "windows.jsonl"
        store.mkdir(parents=True, exist_ok=True)

    def log(self, what: str, t0: float, t1: float, **kw) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps({"what": what, "start_utc": _utc(t0), "end_utc": _utc(t1), "start": t0, "end": t1, **kw}) + "\n")


CHAIN_PROBE = 8 * MiB          # the pre-flight's one filtered read through the whole chain (pod, kubectl exec to data-site_ay, ssh here), timed
BACKFILL_GUESS = 3 * 10 ** 9   # bytes from main's first start (inferred from the monitor's sizes) for the time estimate


def _line_span(remote, a: int, b: int) -> tuple[int, int]:
    """[a', b') inside [a, b) whose ends are line starts: a' after the first newline at or past a, b' after the last newline before b."""
    head = remote.read_range(a, min(65536, b - a)) if a > 0 else b"\n"
    i = head.find(b"\n")
    lo = a + i + 1 if a > 0 and i >= 0 else a
    tail = remote.read_range(max(lo, b - 65536), b - max(lo, b - 65536))
    j = tail.rfind(b"\n")
    hi = max(lo, b - 65536) + j + 1 if j >= 0 else lo
    return lo, hi


def preflight(remote, out: Path, *, users: list[str] | None = None, wait_s: float = 60.0, sleep: Callable[[float], None] = time.sleep,
              now: Callable[[], float] = time.time) -> dict:
    """Read-only. Returns the summary also written to out/preflight.json; `ok` False lists why the backfill must not run. With `users`, one filtered read of
    the last CHAIN_PROBE bytes is timed end to end: the rate the backfill will run at, compression where it happens included."""
    out.mkdir(parents=True, exist_ok=True)
    w = Windows(out)
    why: list[str] = []
    t = now()
    tools = remote.tools()
    w.log("tools", t, now())
    missing = [k for k in (*NEEDED_POD, *NEEDED_DSK) if not tools.get(k)]
    if missing:
        why.append(f"missing tools: {missing}")
    pod_gzip = bool(tools.get("gzip_pod"))
    if hasattr(remote, "pod_gzip"):
        remote.pod_gzip = pod_gzip          # compress before the WAN when the pod can: kubectl exec carries the pod's output to data-site_ay in Azure
    t = now()
    s1 = remote.stat()
    w.log("stat", t, now(), inode=s1.inode, size=s1.size)
    sleep(wait_s)
    t2a = now()
    s2 = remote.stat()
    w.log("stat", t2a, now(), inode=s2.inode, size=s2.size)
    if s2.inode != s1.inode:
        why.append(f"the inode changed between two stats ({s1.inode} -> {s2.inode})")
    if s2.size < s1.size:
        why.append(f"the file shrank between two stats ({s1.size} -> {s2.size})")
    t = now()
    sibs = remote.siblings()
    w.log("siblings", t, now(), n=len(sibs))
    if sibs:
        why.append(f"rotated siblings in the log dir: {sibs}")
    reads = {}
    for name, off, n in (("read_4k_mid", s2.size // 2, 4096), ("read_100m_eof", max(0, s2.size - PROBE_BIG), min(PROBE_BIG, s2.size))):
        t = now()
        secs, got = remote.timed_read(off, n)
        w.log(name, t, now(), off=off, n=n, got=got, pod_s=secs)
        reads[name] = {"off": off, "n": n, "got": got, "pod_s": secs, "wall_s": round(now() - t, 3)}
        if got != n:
            why.append(f"{name}: asked {n} bytes at {off}, got {got}")
    chain = None
    if users and not why:
        lo, hi = _line_span(remote, max(0, s2.size - CHAIN_PROBE), s2.size)
        t = now()
        data = remote.read_filtered(lo, hi, users)
        t1 = now()
        w.log("chain_read", t, t1, from_off=lo, to_off=hi, out_bytes=len(data))
        rate = (hi - lo) / max(t1 - t, 1e-6)
        chain = {"from_off": lo, "to_off": hi, "bytes": hi - lo, "lines_out": data.count(b"\n"), "wall_s": round(t1 - t, 3),
                 "bytes_per_s": round(rate), "backfill_estimate_s": round(BACKFILL_GUESS / rate) if rate else None}
    res = {"utc": _utc(now()), "ok": not why, "why_not": why, "tools": tools, "pod_gzip": pod_gzip, "chain_read": chain,
           "transport": getattr(remote, "transport", None), "path": str(getattr(remote, "path", "")) or None,
           "stat1": {"inode": s1.inode, "size": s1.size}, "stat2": {"inode": s2.inode, "size": s2.size},
           "growth_bytes_per_s": round((s2.size - s1.size) / max(wait_s, 1e-9), 1), "siblings": sibs, "reads": reads,
           "ionice_used": bool(tools.get("ionice")) and bool(tools.get("nice"))}
    (out / "preflight.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    return res


PROBE_POLL_S = 60.0             # while a T live probe is above its limit, the backfill waits and asks again this often (science, #34 08:52Z)
PACE_S = 8.0                    # with a rate cap, one pull reads at most this many seconds' worth of bytes, so no read bursts far past the cap (Astra)
STATE_23 = "/mnt/volume2/icsa-2027/runs/campaign/state.sqlite"
# read-only (sqlite's mode=ro): the latest T live probe's event in .23's store
PROBE_CMD = ("python3 -I -c " + shlex.quote(
    "import json, sqlite3; c = sqlite3.connect('file:" + STATE_23 + "?mode=ro', uri=True); "
    "r = c.execute(\"select id, ts, detail from events where kind = 'live_check_probe' and detail like 'T:%' order by id desc limit 1\").fetchone(); "
    "print(json.dumps(r))") + "; echo ICSA_RC=$?")


def probe_t_23(run=None) -> tuple[int, str] | None:
    """(event id, detail) of `.23`'s latest T live probe, or None when it cannot be read (the backfill then waits: not known is not clean)."""
    import subprocess
    from .solo import SSH_23
    try:
        r = (run or subprocess.run)([*SSH_23, PROBE_CMD], capture_output=True, timeout=60, env={**os.environ, "SSH_AUTH_SOCK": ""})
        out = (r.stdout.decode() if isinstance(r.stdout, bytes) else r.stdout).strip().splitlines()
        if r.returncode != 0 or not out or out[-1] != "ICSA_RC=0":
            return None
        row = json.loads(out[-2])
        return (int(row[0]), str(row[2])) if row else None
    except Exception:  # noqa: BLE001 -- unreadable: the caller waits
        return None


def _probe_clear(p) -> bool:
    return p is not None and p[1].startswith("T: within the limit")


def backfill(remote, store: Path, users: list[str], since: float, *, max_bytes: int = 512 * MiB, now: Callable[[], float] = time.time,
             log: Callable[[str], None] = lambda s: print(s, file=sys.stderr), until_store: Path | None = None, rate_bytes_s: float | None = None,
             probe: Callable[[], tuple[int, str] | None] | None = None, sleep: Callable[[float], None] = time.sleep) -> dict:
    """From the line at `since` to the EOF seen when it starts, or with `until_store` to exactly the first byte of that store's live segment (two ledgers that
    join with no gap and no overlap: science, #34 08:52Z), in pulls of at most max_bytes. `rate_bytes_s` caps the bytes read per second; `probe` (the latest
    T live probe) is asked before every pull, and while it is above its limit, or cannot be read, the backfill waits. Stops, with a gap row in the ledger,
    the moment the file is not the one it started on (`pull.PullRefused`); never starts over at 0."""
    from .ledger import Ledger
    led = Ledger(store)
    with led.locked():                       # one puller at a time: a second one (the 15-min loop started too early) raises instead of reading the same bytes
        return _backfill(remote, led, Windows(store), users, since, max_bytes=max_bytes, now=now, log=log, until_store=until_store,
                         rate_bytes_s=rate_bytes_s, probe=probe, sleep=sleep)


def _backfill(remote, led, w, users, since, *, max_bytes, now, log, until_store=None, rate_bytes_s=None, probe=None, sleep=time.sleep) -> dict:
    """At least one pull always runs, so a file that shrank or was replaced since the last run is refused (with a gap) even when there is nothing to read
    (Codex Astra, #3). A fresh ledger: siblings are checked and the inode noted BEFORE the bisection reads anything, and the first pull must find that
    inode (`start_inode`), so a file replaced during the bisection cannot be read from an offset found in another (Astra, #4)."""
    from .pull import PullRefused, offset_at_time, pull_once
    t = now()
    st0 = remote.stat()
    w.log("stat", t, now(), inode=st0.inode, size=st0.size)
    if until_store is not None:
        seg_p = Path(until_store) / "segment.json"
        if not seg_p.is_file():
            raise SystemExit(f"backfill: no live segment at {until_store} (start the pull first: pull --start-at-eof)")
        seg = json.loads(seg_p.read_text())
        if seg["inode"] != st0.inode:
            raise PullRefused(f"the live segment follows inode {seg['inode']}, the log is {st0.inode}: the two would not join")
        eof0 = int(seg["start_off"])
    else:
        eof0 = st0.size
    paused = [0.0]

    def gate():                                          # a T probe above its limit, or none readable: wait, and ask again; before any read of the log
        if probe is None:
            return
        p = probe()
        while not _probe_clear(p):
            w.log("probe_pause", now(), now(), probe=None if p is None else p[1][:120])
            log(f"backfill: paused ({'the T probe could not be read' if p is None else p[1][:80]})")
            sleep(PROBE_POLL_S)
            paused[0] += PROBE_POLL_S
            p = probe()
    if rate_bytes_s:
        max_bytes = min(max_bytes, max(65536, int(rate_bytes_s * PACE_S)))
    start = start_inode = None
    if led.offset() is None:
        gate()
        t = now()
        sibs = remote.siblings()
        w.log("siblings", t, now(), n=len(sibs))
        if sibs:
            raise PullRefused(f"rotated sibling(s) before the backfill: {sibs}; nothing was read")
        t = now()
        start, start_inode = offset_at_time(remote, since), st0.inode
        w.log("bisect", t, now(), since_utc=_utc(since), offset=start, inode=start_inode)
        cap = led.root / "capture.json"                  # where the capture begins: every line from `since` on is in the ledger (the extraction's lower bound)
        tmp = cap.with_name("capture.json.tmp")
        tmp.write_text(json.dumps({"covered_from": since, "since_utc": _utc(since), "offset": start, "inode": start_inode, "until_off": eof0}))
        tmp.replace(cap)
        log(f"backfill: {_utc(since)} is at byte {start} of {eof0} (inode {start_inode})")
    n = 0
    while True:
        gate()
        t = now()
        row = pull_once(remote, led, users, max_bytes=max_bytes, start_offset=start, start_inode=start_inode, min_size=eof0, now=now,
                        end_limit=eof0 if until_store is not None else None)
        t1 = now()
        w.log("pull", t, t1, seq=row.get("seq"), from_off=row.get("from_off"), to_off=row.get("to_off"), n_lines=row.get("n_lines"))
        if row.get("seq") is None:
            break
        n += 1
        log(f"backfill: pull {row['seq']}: bytes {row['from_off']}..{row['to_off']} of {eof0}, {row['n_lines']} lines")
        if rate_bytes_s:                                 # the cap: as long as reading these bytes at the rate would take
            rest = (row["to_off"] - row["from_off"]) / rate_bytes_s - (t1 - t)
            if rest > 0:
                sleep(rest)
        if led.offset() >= eof0 or row["to_off"] == row["from_off"]:          # caught up, or a pull that moved nothing: stop
            break
    return {"pulls": n, "eof_at_start": eof0, "offset": led.offset(), "start": start, "paused_s": paused[0]}


def pull_live(remote, led, users: list[str], *, max_bytes: int, now: Callable[[], float] = time.time) -> dict:
    """The incremental pull (science, #34 08:52Z): an empty ledger starts at the log's current EOF, cut to a line start, and notes it in segment.json (the
    backfill's join); after that, each call reads the new bytes from the ledger's offset."""
    from .pull import pull_once
    seg = led.root / "segment.json"
    if led.offset() is None and seg.is_file():          # the join, once written, never moves: the backfill ends there (Astra)
        d = json.loads(seg.read_text())
        return pull_once(remote, led, users, max_bytes=max_bytes, start_offset=int(d["start_off"]), start_inode=int(d["inode"]), now=now)
    if led.offset() is None:
        st = remote.stat()
        w = max(0, st.size - 65536)
        tail = remote.read_range(w, st.size - w) if st.size > w else b""
        k = tail.rfind(b"\n")
        start = w + k + 1 if k >= 0 else w
        led.root.mkdir(parents=True, exist_ok=True)
        tmp = seg.with_name("segment.json.tmp")
        tmp.write_text(json.dumps({"start_off": start, "inode": st.inode, "covered_from": now(), "since_utc": _utc(now())}))
        tmp.replace(seg)
        return pull_once(remote, led, users, max_bytes=max_bytes, start_offset=start, start_inode=st.inode, now=now)
    return pull_once(remote, led, users, max_bytes=max_bytes, now=now)


def preflight_reduced(remote, out: Path, *, wait_s: float = 60.0, sleep: Callable[[float], None] = time.sleep, now: Callable[[], float] = time.time) -> dict:
    """Science, #34 08:52Z: under main, only the stat and the sibling listing; no timed read and no chain read, which would measure site_g under load. The tools
    are not checked: a pod without nice or ionice fails the first pull loudly. gzip runs on site_g's node (site_g-direct), not in the pod."""
    out.mkdir(parents=True, exist_ok=True)
    w = Windows(out)
    why: list[str] = []
    t = now()
    s1 = remote.stat()
    w.log("stat", t, now(), inode=s1.inode, size=s1.size)
    sleep(wait_s)
    t = now()
    s2 = remote.stat()
    w.log("stat", t, now(), inode=s2.inode, size=s2.size)
    if s2.inode != s1.inode:
        why.append(f"the inode changed between two stats ({s1.inode} -> {s2.inode})")
    if s2.size < s1.size:
        why.append(f"the file shrank between two stats ({s1.size} -> {s2.size})")
    t = now()
    sibs = remote.siblings()
    w.log("siblings", t, now(), n=len(sibs))
    if sibs:
        why.append(f"rotated siblings in the log dir: {sibs}")
    res = {"utc": _utc(now()), "ok": not why, "why_not": why, "reduced": True, "tools": {}, "reads": {}, "pod_gzip": False, "chain_read": None,
           "stat1": {"inode": s1.inode, "size": s1.size}, "stat2": {"inode": s2.inode, "size": s2.size}, "siblings": sibs,
           "growth_bytes_per_s": round((s2.size - s1.size) / max(wait_s, 1e-9), 1), "transport": getattr(remote, "transport", None),
           "path": str(getattr(remote, "path", "")) or None}
    (out / "preflight.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    return res


def checked_preflight_at(pf: Path) -> dict | None:
    d = json.loads(pf.read_text()) if pf.is_file() else None
    if not d or not d.get("ok"):
        print(f"icsa.faults.mainaudit: no passing pre-flight at {pf}", file=sys.stderr)
        return None
    return d


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def manifests(store: Path, ids_path: Path | None = None, build=None) -> dict:
    """The S1 and S2 manifests as fault calibration builds them (`calibrate._manifests`): from the local copies of the dataset (never site_g), with every
    file's REST id from the full index's ids.json (its sha256 checked against PROVENANCE.json), without which no gate read maps to a file (Codex Astra,
    full review #1). Kept in the store, keyed by that sha256: another ids.json rebuilds them."""
    from icsa.faults import calibrate as C
    from icsa.records import Layout

    from .extract import manifest_from_json, manifest_to_json
    ids_path = Path(ids_path or C.IDS)
    _, sha = C.load_ids(ids_path)
    p = store / "manifests" / f"manifests-{sha[:16]}.json"
    if not p.is_file():
        mans, sha2 = (build or C._manifests)(ids_path)
        if sha2 != sha:
            raise SystemExit(f"{ids_path} changed while the manifests were built")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps({"ids_sha256": sha, **{lay.value: manifest_to_json(m) for lay, m in mans.items()}}))
        tmp.replace(p)
    d = json.loads(p.read_text())
    out = {Layout(k): manifest_from_json(d[k]) for k in ("S1", "S2")}
    missing = [f.key for m in out.values() for f in m.files if not f.object_id]
    if missing:
        raise SystemExit(f"{len(missing)} manifest file(s) without a REST id, first {missing[:3]}: the gate's reads could not be mapped")
    return out


def exec_hosts(mirror: Path) -> dict[str, str]:
    """<run_key>/<attempt dir> -> the host it ran on, from the mirror's store (attempts.exec_host); '' where the store has none."""
    import sqlite3
    dbs = sorted(mirror.glob("**/state.sqlite"))
    if not dbs:
        return {}
    con = sqlite3.connect(f"file:{dbs[0]}?mode=ro", uri=True)
    try:
        return {"/".join(Path(d).parts[-2:]): (h or "") for d, h in con.execute("select run_dir, exec_host from attempts where run_dir is not null")}
    finally:
        con.close()


def parse_quarantines(args: list[str]) -> dict[str, dict]:
    """--quarantines HOST=PATH (entries, as of the copy's mtime) or HOST=absent@ISO (no file at that time: no quarantine ever on that host)."""
    quar = {}
    for hp in args:
        h, _, p = hp.partition("=")
        if p.startswith("absent@"):
            quar[h] = {"entries": [], "as_of": _epoch(p[len("absent@"):])}
        else:
            qp = Path(p)
            if not qp.is_file():
                raise SystemExit(f"--quarantines {hp}: no such file (a host never quarantined: HOST=absent@ISO)")
            quar[h] = {"entries": _jsonl(qp), "as_of": qp.stat().st_mtime}
    return quar


def segments(root: Path) -> dict:
    """The capture as extraction reads it (science, #34 08:52Z): the live segment (root/live, from the EOF when the pull began) and the backfill (root/backfill,
    from main's first start). Once the backfill has reached exactly the live segment's first byte on the same inode, they are one capture: the backfill's
    lines then the live ones, from the backfill's `since`. Before that only the live segment counts, from its own start: a run before it is not observed
    (capture_starts_after_lease), never credited from a backfill still on its way."""
    from itertools import chain
    from .ledger import Ledger
    live, back = Ledger(root / "live"), Ledger(root / "backfill")
    seg_p = root / "live" / "segment.json"
    if not seg_p.is_file():
        raise SystemExit(f"no live segment at {seg_p.parent}: start the pull (pull --start-at-eof)")
    seg = json.loads(seg_p.read_text())
    cap_p = root / "backfill" / "capture.json"
    joined = back.offset() is not None and back.offset() == int(seg["start_off"]) and back.inode() == int(seg["inode"]) and cap_p.is_file()
    if joined:
        return {"joined": True, "covered_from": json.loads(cap_p.read_text())["covered_from"], "lines": lambda: chain(back.iter_lines(), live.iter_lines()),
                "covered_until": live.covered_until(), "gaps": back.gaps() + live.gaps(),
                "provenance": {"backfill_offset": back.offset(), "live_start": seg["start_off"], "live_offset": live.offset(), "inode": live.inode()}}
    return {"joined": False, "covered_from": seg["covered_from"], "lines": live.iter_lines, "covered_until": live.covered_until(), "gaps": live.gaps(),
            "provenance": {"live_start": seg["start_off"], "live_offset": live.offset(), "inode": live.inode(), "backfill_offset": back.offset()}}


def capture_of(store: Path) -> dict:
    """The capture extraction reads: a provider's store (`provider.json`, written by `provider.pull_cycle`: its rotated and live files, in order) or site_g's (live
    segment and backfill). A provider's `--mon` is its `mon.jsonl` (`watch.record`) and its `--restart-log` the empty `restart_log.jsonl` beside it."""
    from . import provider as PV
    return PV.segments(store) if (store / "provider.json").is_file() else segments(store)


def run_extract(a) -> dict:
    from icsa import opwrestart
    from icsa.faults.units import Required
    from icsa.instances import load as IL

    from . import windows as W
    from .extract import attempts, extract
    store, mirror = Path(a.store), Path(a.mirror)
    cap = capture_of(store)
    mon = _jsonl(a.mon)                              # read once: restart detection and its coverage from the same samples (delta #6)
    restarts = W.restart_windows(opwrestart.read_log(a.restart_log), mon, host="site_g")
    span = W.mon_span(mon)
    quar = parse_quarantines(a.quarantines)
    dbs = sorted(mirror.glob("**/state.sqlite"))
    if not dbs:          # without the store neither the run hosts nor the killed attempts are known: orphan risk would read as none (silent-fallback B)
        raise SystemExit(f"icsa.faults.mainaudit extract: no state.sqlite under {mirror}")
    hosts = exec_hosts(mirror)
    req_cache: dict = {}
    extents = IL.load_required_extents()

    def required_of(iid):
        if iid not in req_cache:
            req_cache[iid] = Required.from_parted(extents[iid])
        return req_cache[iid]

    def host_of(d: Path, rec: dict):
        return hosts.get("/".join(d.parts[-2:]))     # the store names the run host's path; the mirror keeps it under its own root
    from icsa.faults import calibrate as C
    from . import switched as SW
    switched_key = f"{SW.SCHEMA}|{C.load_ids(Path(a.ids or C.IDS))[1]}"
    every = attempts(mirror, OPTIONS)                    # any run's sandbox start reaps every orphan on its host, whatever the option
    orphans = W.orphan_windows(W.killed_attempts(dbs[0]), W.reaps_from_records(every, host_of))
    return extract(store, attempts(mirror, [o for o in a.options.split(",") if o]), cap["lines"], covered_until=cap["covered_until"], gaps=cap["gaps"],
                   restarts=restarts, quarantines=quar, manifests=manifests(store, a.ids), required_of=required_of, host_of=host_of,
                   provenance={**cap["provenance"], "joined": cap["joined"]}, orphans=orphans, mon_span=span, covered_from=cap["covered_from"],
                   switched_key=switched_key)


def run_solo(a) -> int:
    """Any failure prints an INCONCLUSIVE result and exits 3: the check never ends in silence or in SOLO by default."""
    import shlex
    from . import solo as SO
    try:
        slot_map = json.loads(Path(a.slot_map).read_text())
        users = sorted({v["user"] for v in slot_map.values()})
        if a.dry_run:
            print("\n".join(_remote(dry_run=True, transport=a.transport).describe(users)))
            print("# .23's leases (read-only: each lock file's inode against /proc/locks; no lock is taken)")
            print("SSH_AUTH_SOCK= " + shlex.join([*SO.SSH_23, SO.LEASES_CMD]))
            return 0
        launch = json.loads(Path(a.launch).read_text())
        r = _remote(transport=a.transport)
        t0 = time.time()
        tail = SO.tail_users(r, minutes=a.minutes, max_bytes=a.max_bytes, local_now=time.time())
        try:
            Windows(Path(a.store)).log("solo", t0, time.time(), from_off=tail["from_off"], to_off=tail["to_off"])
        except OSError as e:                                   # the record of the read is wanted, but its loss must not cost the answer
            print(f"icsa.faults.mainaudit solo: the read's window could not be logged: {e}", file=sys.stderr)
        try:
            held = SO.held_keys(SO.run_23(SO.LEASES_CMD))
        except Exception as e:  # noqa: BLE001 -- unreadable is INCONCLUSIVE, said in the result
            print(f"icsa.faults.mainaudit solo: .23's leases: {type(e).__name__}: {e}"[:400], file=sys.stderr)
            held = None
        code, out = SO.verdict(tail, held, a.exclude, slot_map, SO.owners(launch))
    except Exception as e:  # noqa: BLE001 -- never a traceback in place of an answer
        code, out = 3, {"result": f"INCONCLUSIVE: {type(e).__name__}: {e}"[:600]}
    print(SO.dumps(code, out))
    return code


EXIT_REFUSED, EXIT_TRANSIENT, EXIT_BUSY = 4, 5, 6      # the loop (tools/m_audit_loop.sh): 4 stops it (a gap is on record: a person must look), 5 retries next round, 6 skips one


def _remote(**kw):
    from .remote import DskRemote
    return DskRemote(**kw)


def _guarded(fn) -> int:
    """A refusal (the file is not the one the ledger follows) is final until a person looks; a transport error is not; a held ledger means another puller."""
    import subprocess
    from .ledger import LedgerError
    from .pull import PullRefused
    try:
        return fn()
    except PullRefused as e:
        print(f"icsa.faults.mainaudit: REFUSED (a gap is on record; no more pulls until a person looks): {e}", file=sys.stderr)
        return EXIT_REFUSED
    except LedgerError as e:
        print(f"icsa.faults.mainaudit: busy: {e}", file=sys.stderr)
        return EXIT_BUSY
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as e:
        print(f"icsa.faults.mainaudit: transient: {type(e).__name__}: {e}"[:600], file=sys.stderr)
        return EXIT_TRANSIENT


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.faults.mainaudit", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--out", default=str(STORE / "preflight"))
    p.add_argument("--wait-s", type=float, default=60.0)
    p.add_argument("--dry-run", action="store_true", help="print the remote command lines and run nothing")
    p.add_argument("--transport", choices=("site_g-direct", "dsk"), default="site_g-direct", help="site_g-direct: ssh to site_g's node and its k3s kubectl (default); dsk: dsk.sh via data-site_ay")
    p.add_argument("--no-timed-reads", action="store_true", help="science, #34 08:52Z: under main, only the stat and the sibling listing")
    b = sub.add_parser("backfill")
    b.add_argument("--store", default=str(STORE))
    b.add_argument("--since", required=True, help="ISO UTC, e.g. 2026-11-04T00:33:45Z (main's first start)")
    b.add_argument("--max-bytes", type=int, default=512 * MiB)
    b.add_argument("--dry-run", action="store_true")
    b.add_argument("--transport", choices=("site_g-direct", "dsk"), default="site_g-direct")
    b.add_argument("--preflight", default=None, help="the pre-flight's preflight.json (default <store>/preflight/preflight.json)")
    b.add_argument("--until-store", default=None, help="the live pull's store: the backfill ends exactly at its first byte (two segments, no gap, no overlap)")
    b.add_argument("--rate-mb-s", type=float, default=None, help="cap the bytes read, in MB/s (science: 1)")
    b.add_argument("--no-probe-watch", action="store_true", help="do not pause on .23's T live probe (the default pauses while it is above its limit)")
    q = sub.add_parser("pull")
    q.add_argument("--store", default=str(STORE))
    q.add_argument("--max-bytes", type=int, default=256 * MiB)
    q.add_argument("--transport", choices=("site_g-direct", "dsk"), default="site_g-direct")
    q.add_argument("--preflight", default=None, help="the pre-flight's preflight.json (default <store>/preflight/preflight.json)")
    q.add_argument("--start-at-eof", action="store_true", help="an empty ledger starts at the log's current EOF (the live segment; science, #34 08:52Z)")
    e = sub.add_parser("extract", help="one record per finished attempt, from the pulled lines (no remote read)")
    e.add_argument("--store", default=str(STORE))
    e.add_argument("--mirror", default="/mnt/volume2/icsa-2027/coding-mirror")
    e.add_argument("--options", default=",".join(OPTIONS))
    e.add_argument("--restart-log", required=True, help="a copy of site_g_restart_log.jsonl (hash chain checked)")
    e.add_argument("--mon", required=True, help="a copy of site_g's monitor log mon.jsonl (unplanned restarts)")
    e.add_argument("--quarantines", action="append", default=[], help="per run host: HOST=PATH (a copy of its quarantines.jsonl, as of the file's mtime) "
                   "or HOST=absent@ISO (the file did not exist at that time: no quarantine ever). A host given neither leaves its runs' ends unverified")
    e.add_argument("--ids", default=None, help="the full index's ids.json (REST ids; default calibrate.IDS)")
    so = sub.add_parser("solo", help="is site_g solo? slot users in the log's last minutes that .23 holds no lease on (science, #34 07:46Z)")
    so.add_argument("--launch", required=True, help="the campaign's launch JSON: hosts' slot_keys, the live check's keys, the reservations")
    so.add_argument("--slot-map", default=str(REPO / "config" / "slot_map.json"))
    so.add_argument("--minutes", type=float, default=5.0)
    so.add_argument("--exclude", action="append", default=[], help="a slot key allowed to read (the probe's own, e.g. T-27); repeat")
    so.add_argument("--max-bytes", type=int, default=128 * MiB, help="the tail read's bound; too small for the window gives INCONCLUSIVE, never SOLO")
    so.add_argument("--store", default=str(STORE), help="where its read's window is logged (windows.jsonl)")
    so.add_argument("--transport", choices=("site_g-direct", "dsk"), default="site_g-direct")
    so.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("status")
    s.add_argument("--store", default=str(STORE))
    sub.add_parser("pin", help="the sha256 that freezes the measure's code")
    m = sub.add_parser("measure", help="H3's agent-run measure: counts.json, self_report.json, record.json, record.csv (the code is pinned; no value is printed)")
    m.add_argument("--pin", required=True, help="a file holding the pin (`pin`'s output); the command refuses (exit 3) unless the code hashes to it")
    m.add_argument("--scored", required=True, help="scored_rows.jsonl")
    m.add_argument("--platform", required=True, help="platform_rows.jsonl (extract's join file)")
    m.add_argument("--out", required=True, help="the directory for counts.json, self_report.json, record.json and record.csv")
    m.add_argument("--day-truth", default=None, help="daytruth.py's output directory: enables the record measure's stricter readings (i) and (ii); the code that made it must be this tree's labeller")
    a = ap.parse_args(argv)
    if a.cmd in ("pin", "measure"):          # before anything reads a config or an input: the pin comes first
        from . import measure
        if a.cmd == "pin":
            print(measure.pin_hash(REPO))
            return 0
        print(json.dumps(measure.run(REPO, a.pin, a.scored, a.platform, a.out, a.day_truth), indent=1, sort_keys=True))
        return 0
    if a.cmd == "status":
        from .ledger import Ledger
        led = Ledger(Path(a.store))
        print(json.dumps({"offset": led.offset(), "inode": led.inode(), "covered_until": led.covered_until(), "gaps": led.gaps()}, indent=1))
        return 0
    if a.cmd == "solo":
        return run_solo(a)
    if a.cmd == "extract":
        print(json.dumps(run_extract(a), indent=1, sort_keys=True))
        return 0
    users = slot_users()
    if getattr(a, "dry_run", False):
        r = _remote(dry_run=True, transport=a.transport)
        print("\n".join(r.describe(users)))
        return 0
    def checked_preflight(store: Path) -> dict | None:
        pf = store / "preflight" / "preflight.json"
        d = json.loads(pf.read_text()) if pf.is_file() else None
        if not d or not d.get("ok"):
            print(f"icsa.faults.mainaudit: no passing pre-flight at {pf}: run `preflight --out {pf.parent}` first", file=sys.stderr)
            return None
        return d
    if a.cmd == "preflight":
        r = _remote(transport=a.transport)
        res = (preflight_reduced(r, Path(a.out), wait_s=a.wait_s) if a.no_timed_reads else preflight(r, Path(a.out), users=users, wait_s=a.wait_s))
        print(json.dumps(res, indent=1, sort_keys=True))
        return 0 if res["ok"] else 3
    if a.cmd == "backfill":
        pf = checked_preflight_at(Path(a.preflight) if a.preflight else Path(a.store) / "preflight" / "preflight.json")
        if pf is None:
            return 3
        r = _remote(pod_gzip=bool(pf.get("pod_gzip")), transport=a.transport)

        def go():
            print(json.dumps(backfill(r, Path(a.store), users, _epoch(a.since), max_bytes=a.max_bytes, until_store=Path(a.until_store) if a.until_store else None,
                                      rate_bytes_s=a.rate_mb_s * 1e6 if a.rate_mb_s else None, probe=None if a.no_probe_watch else probe_t_23), indent=1))
            return 0
        return _guarded(go)
    if a.cmd == "pull":
        from .ledger import Ledger
        from .pull import pull_once
        pf = checked_preflight_at(Path(a.preflight) if a.preflight else Path(a.store) / "preflight" / "preflight.json")
        if pf is None:
            return 3
        r = _remote(pod_gzip=bool(pf.get("pod_gzip")), transport=a.transport)
        led = Ledger(Path(a.store))
        if led.offset() is None and not a.start_at_eof:
            print("icsa.faults.mainaudit: the ledger is empty: run backfill first, or start the live segment with --start-at-eof", file=sys.stderr)
            return 3
        if led.rows() and led.rows()[-1].get("kind") == "gap":
            print("icsa.faults.mainaudit: the ledger's last row is a gap: no pull until a person has looked (start a new store to go on)", file=sys.stderr)
            return EXIT_REFUSED

        def go():
            t = time.time()
            with led.locked():
                row = pull_live(r, led, users, max_bytes=a.max_bytes)
            Windows(Path(a.store)).log("pull", t, time.time(), seq=row.get("seq"), from_off=row.get("from_off"), to_off=row.get("to_off"), n_lines=row.get("n_lines"))
            print(json.dumps(row, indent=1))
            return 0
        return _guarded(go)
    return 2


if __name__ == "__main__":
    sys.exit(main())
