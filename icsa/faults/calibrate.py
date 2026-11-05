"""The calibration runner (#11 part 2): executes the sealed, claimed plan, pulls our lines, scores them.

    python -m icsa.faults.calibrate plan  --out DIR --seed N --ids IDS.json      build, seal the masking verdicts, claim ONCE
    python -m icsa.faults.calibrate run   --out DIR --image TAG|ID (--logcheck-heartbeat F | --logcheck-off REASON) [--pause-file F] [--concurrency N] [--seam]
                                                                                 execute pending runs, one sandbox per run
    python -m icsa.faults.calibrate pull  --out DIR                              our audit and Traefik lines, filtered at source
    python -m icsa.faults.calibrate score --out DIR                              rows for fidelity and #14's adapter
    python -m icsa.faults.calibrate verdict --out DIR                            per-cell verdict; exits 3 on a partial matrix
    python -m icsa.faults.calibrate logcheck --out DIR [--heartbeat F]           exits 4 before Traefik could drop unpulled lines; F is what `run` reads

Rules (science and the parent, #11 and amendment 12):
- The plan is `matrix.calibration_plan`: built, its per-run masking verdicts sealed, claimed in the ledger once. A claimed
  run is run once; a failed one is lost and gets a replacement from the same row and seed, as a fresh attempt with its own
  run key, at most 3 attempts, before any cell is scored; one that fails them all leaves its cell incomplete (`ledger`).
- Every run holds a slot-user lease of its option and its own run key `s11cal-<matrix sha8>-<order>-<scenario>`, added as
  X-ICSA-Run by the gate; `require_lease_and_key` refuses a run without both, before any sandbox starts.
- The read plan is exactly `script.execute`'s; in the sandbox T reads through ONE fs.open per file per run (agents'
  client, read-ahead included), D downloads with fs.get, M reads the mount; M's condition flags are the frozen ones
  (`CONDITION_ARGS`), warm_buffer pre-reads the run's days, then waits `WARM_GAP_S` outside the run's window.
- Attribution only by slot user (audit), run key (Traefik) and the run's own perf CSV: never the time-only fallback.
- Logs come through `day0/scripts/dsk.sh`, read-only, filtered at the source to our slot users and our run keys.
- Resumable per run; a pause file stops it at a run boundary; every sandbox is stopped on every exit path, and a slot
  whose sandbox may survive is quarantined until its teardown is proven (the live check's rule).
- Actual reads are checked against the plan. The one rule for a short read (science, #2, 2 Nov): the run is invalid and
  re-run like any failed run, decided from its own byte counts before any scoring. Its truth never comes from what was read,
  because the sealed masking verdict and the injected set are both functions of the plan.
- A record is scored only if it is shown to have recorded the run (see `not_observed`). A run with no attributed lines, or
  with requests the gate forwarded that Traefik does not hold under its run key, is not observed: invalid, never detected.
- Every run's window enters attribution, failed and lost ones included (see `score`).
- A capture is never overwritten: every pull is kept by hash and new lines are appended. Traefik rotates at 1 GiB, keeping 16,
  so a pull reads the live file and every sibling, and `logcheck` alarms before files no pull has read could drop; the audit log
  does not rotate today, so a sibling of it stops the pull (see `pull_logs`).
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from icsa.records import Layout, Option

from .ledger import MAX_ATTEMPTS, Ledger
from .live_check import QUARANTINED_LEASES, QUARANTINED_UNTIL, _redact, hold_quarantines
from .masking import _Recorder
from .scenarios import Condition, Scenario
from .script import execute as script_execute
from .units import Manifest, Required

PREFIX = "s11cal-"
RUN_KEY_RE = re.compile(r"^s11cal-[0-9a-f]{8}-\d{4}-[A-Za-z0-9_.-]{1,120}$")
MEASURE_KEY_RE = re.compile(r"^s11cal-measure-[A-Za-z0-9_.-]{1,60}$")    # the raw-read timing runs, never scored
VALIDATION_KEY_RE = re.compile(r"^s11val-[0-9a-f]{8}-\d{4}-[A-Za-z0-9_.-]{1,120}$")   # amendment 17(c)'s validation set (gate_validation.py), never calibration
_CALIBRATION_ROUTE = object()
CONDITION_ARGS = {Condition.COLD: [], Condition.WARM_BUFFER: [],
                  Condition.PREFETCH_ON: ["--read-buffer-prefetch-duration", "30", "--read-buffer-max-size", "1073741824"]}
WARM_GAP_S = 6.0            # > the attribution margin (2 s) on both sides: the pre-read stays outside the run's window
# The run's token outlives federation.RUN_TIME_CAP_S plus the harness margin (SlotTokens); the exec, warm pre-read
# included, is bounded inside that cap with room for sandbox start and teardown, so a token never expires mid-run.
START_TEARDOWN_S = 600
RESULT_TAG = "ICSA_CAL "
PERF_MARGIN_S = 2.0         # the attribution margin, < WARM_GAP_S
REPO = Path(__file__).resolve().parents[2]


_LAYERS: dict = {}


def layers_fingerprint(image_id: str | None) -> str | None:
    """sha256 of the image's RootFS layer list (docker inspect): equal content under different ids/tags shows equal."""
    if not image_id:
        return None
    if image_id not in _LAYERS:                  # only successes are cached: a failed inspect is retried next run
        try:
            p = subprocess.run(["docker", "image", "inspect", "-f", "{{json .RootFS.Layers}}", image_id],
                               capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if p.returncode != 0 or not p.stdout.strip():
            return None
        import hashlib
        _LAYERS[image_id] = hashlib.sha256(p.stdout.encode()).hexdigest()
    return _LAYERS[image_id]


def exec_timeout_s() -> float:
    from icsa.scripted.federation import RUN_TIME_CAP_S
    return float(RUN_TIME_CAP_S - START_TEARDOWN_S)


class RunRefused(RuntimeError):
    """A run without its slot lease or its run key never starts."""


import threading as _threading

ADMIT = _threading.RLock()   # quarantine publication and the check+start of a sandbox are one critical section


class QuarantineInForce(RunRefused):
    """Another run's slot is quarantined (its sandbox may survive): no new sandbox starts in this process."""


class NoSandboxStarted(RunRefused):
    """`Sandbox.start` refused the run before any container existed (a moved image tag, a rejected config): no attempt used, the batch stops for a look."""


def utc_ms() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def run_key(claim_sha: str, order: int, s: Scenario) -> str:
    return f"{PREFIX}{claim_sha[:8]}-{order:04d}-{s.sid}"


def attempt_key(claim_sha: str, order: int, s: Scenario, runs_dir: Path) -> str:
    """This attempt's run key and directory: the plain key first, then -a2, -a3. A re-run never shares a key with an earlier
    attempt, so each attempt's X-ICSA-Run lines and record stay its own."""
    return next(k for k in attempt_keys(claim_sha, order, s) if not (runs_dir / k).exists())


def attempt_keys(claim_sha: str, order: int, s: Scenario) -> list[str]:
    base = run_key(claim_sha, order, s)
    return [base] + [f"{base}-a{n}" for n in range(2, MAX_ATTEMPTS + 2)]


def expected_bytes(ops: list, manifest: Manifest) -> list[int]:
    """What each planned operation must return: a range's length, a download's manifest size."""
    return [manifest.file(o[1]).size if o[0] == "download" else o[3] - o[2] for o in ops]


def check_reads(res: dict, ops: list, manifest: Manifest) -> list[str]:
    """Actual reads against the plan; [] if every planned byte came back. A read cannot return more than it asked for, so
    equal totals rule out a short range read in records that hold only the total."""
    want = sum(expected_bytes(ops, manifest))
    errs = []
    for total, short in (("bytes", "short_reads"), ("warm_bytes", "warm_short_reads")):
        if total == "warm_bytes" and total not in res:
            continue
        if res.get(total) != want:
            errs.append(f"short read: {total} {res.get(total)} of the {want} B planned")
        if res.get(short):
            i, exp, got = res[short][0]
            errs.append(f"short read: {len(res[short])} {short} operation(s), first op {i}: {got} of {exp} B")
    return errs


RUN_TAGS: dict = {"traefik_setting": None, "data_path": None}     # set by the `run` command; stamped on every run record
LOGCHECK: dict = {}                                               # how the `run` command stands to the kept-log check; on every run record too


def run_tags() -> dict:
    """Where a run ran, for reporting each cell with and without a setting (science, #2, 2 Nov)."""
    return {"host": socket.gethostname(), **RUN_TAGS}


def require_lease_and_key(lease, key: str) -> None:
    if not (RUN_KEY_RE.match(key or "") or MEASURE_KEY_RE.match(key or "") or VALIDATION_KEY_RE.match(key or "")):
        raise RunRefused(f"run key {key!r} is not s11cal-<sha8>-<order>-<scenario>")
    if lease is None or not getattr(lease, "slot", None) or not getattr(lease, "subject", None):
        raise RunRefused(f"{key}: no slot-user lease (slot and user id): a calibration run never starts without one")


def read_ops(s: Scenario, required: Required, manifest: Manifest) -> list[list]:
    """The script's operations, exactly as `script.execute` issues them (no record, no model)."""
    from .scenarios import read_plan
    rec = _Recorder()
    script_execute(read_plan(s, required), manifest, s.option, rec)
    return [list(op) for op in rec.ops]


_SNIPPET = r'''
import json as _j, os as _os, time as _t, datetime as _dt
def _u():
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds")
_P = _j.loads(PLAN_JSON)
_E = _P.get("expect")
_loc = _os.environ["ICSA_DATASET_LOCATION"].rstrip("/")
_fs = None
if _P["option"] in ("T", "D"):
    import fsspec
    _fs = fsspec.filesystem(_P.get("fs_protocol", "onedata"))   # the agents' client ({FS_EXPR}); "file" in stand-in tests
def _path(key):
    return _loc if _P["layout"] == "S2" else _loc + "/" + key
def _do(ops):
    files, n, short = {}, 0, []
    try:
        for i, op in enumerate(ops):
            p = _path(op[1])
            if op[0] == "download":
                local = "/work/data/dl.bin"
                _os.makedirs("/work/data", exist_ok=True)
                _fs.get(p, local)
                got = _os.path.getsize(local)
                _os.remove(local)
                n += got
                if _E is not None and got != _E[i]:
                    short.append([i, _E[i], got])
                continue
            fh = files.get(p)
            if fh is None:                     # ONE file object per file per run, as agents keep it open
                fh = files[p] = (_fs.open(p, "rb") if _fs is not None else open(p, "rb"))
            fh.seek(op[2])
            got = len(fh.read(op[3] - op[2]))
            n += got
            if _E is not None and got != _E[i]:
                short.append([i, _E[i], got])
    finally:
        for fh in files.values():
            fh.close()
    return n, short[:50]
_out = {}
if _P["warm"]:
    _out["warm_start_utc"] = _u(); _out["warm_bytes"], _out["warm_short_reads"] = _do(_P["ops"]); _out["warm_end_utc"] = _u()
    _t.sleep(_P["gap_s"])
_out["run_start_utc"] = _u()
_out["bytes"], _out["short_reads"] = _do(_P["ops"])
_out["run_end_utc"] = _u()
print("ICSA_CAL " + _j.dumps(_out), flush=True)
'''


def exec_code(s: Scenario, ops: list, fs_protocol: str = "onedata", gap_s: float = WARM_GAP_S,
              expect: list | None = None) -> str:
    plan = {"option": s.option.value, "layout": s.layout.value, "ops": ops, "fs_protocol": fs_protocol,
            "warm": s.condition is Condition.WARM_BUFFER, "gap_s": gap_s, "expect": expect}
    return f"PLAN_JSON = {json.dumps(plan)!r}\n{_SNIPPET}"


def _host_facts() -> dict:
    from icsa.sandbox import hostops
    return hostops.host_facts()


def execute_run(planned, claim, required: Required, manifest: Manifest, cfg, runs_dir: Path, key: str | None = None, *,
                via=_CALIBRATION_ROUTE, code: str | None = None) -> dict:
    """One run: lease, sandbox, the script's reads, teardown. Returns the run record (also written to run.json). `via` and `code` are for the validation set of
    amendment 17(c) (gate_validation.py): its route (None, the campaign's direct one) and its script, which prints its own `ICSA_VAL ` line into `val`."""
    from icsa.harness.real_sandbox import _epoch
    from icsa.sandbox import Sandbox
    from icsa.sandbox import route
    from icsa.sandbox.sandbox import StartRefused
    from icsa.scripted import federation as F
    from icsa.scripted import tokens
    from icsa.scripted.slot_tokens import SlotTokens

    s = planned.scenario
    earlier = [k for k in attempt_keys(claim.sha, planned.order, s) if (runs_dir / k).exists()]
    replaces = None if key else (earlier[-1] if earlier else None)       # a replacement names the attempt it replaces (the one before it, same row and seed)
    key = key or attempt_key(claim.sha, planned.order, s, runs_dir)
    out = runs_dir / key
    out.mkdir(parents=True, exist_ok=False)
    r: dict = {"run_key": key, "sid": s.sid, "order": planned.order, "option": s.option.value, "layout": s.layout.value,
               "condition": s.condition.value, "matrix_sha": getattr(claim, "sha", None), "ok": False, "errors": [], "replaces": replaces,
               "started_utc": utc_ms(), "tags": run_tags(), "logcheck": dict(LOGCHECK),
               # the sandbox image each run measured the records under (the campaign's pinned id for the ramp)
               "image": getattr(cfg, "image", None), "image_id": getattr(cfg, "pinned_image_id", None),
               "host_aliases": dict(sorted((getattr(cfg, "host_aliases", None) or {}).items())), "host": _host_facts(),
               "image_layers_sha256": layers_fingerprint(getattr(cfg, "pinned_image_id", None))}
    secret: list[str] = []
    refused = False
    try:
        ops = read_ops(s, required, manifest)
        r["n_ops"] = len(ops)
        with SlotTokens().lease(key, s.option.value) as lease:
            require_lease_and_key(lease, key)
            lt = lease._lt
            secret.append(lt.token)
            r.update(slot=lease.slot, user_id=lease.subject, lease_start_utc=utc_ms(),
                     token_valid_until_utc=lt.record.valid_until_utc)
            valid_until = _epoch(lt.record.valid_until_utc)
            _save_record(out, r, secret)     # a crash from here on leaves the slot and the start: `score` keeps the window
            sbx = None
            with tokens.held(lease):
                try:
                    try:
                        if via is _CALIBRATION_ROUTE:
                            via = route.fault_calibration_via(s.option)
                        r["provider_route"] = route.route_name(via)        # each run says which path it read by
                        dc = F.data_config(F.MAIN, s.option, via=via, perf_log=(s.option is Option.M),
                                           oneclient_extra_args=CONDITION_ARGS[s.condition] or None)
                        with ADMIT:                   # no sandbox starts once any slot is quarantined (and starts stagger)
                            if QUARANTINED_UNTIL:
                                raise QuarantineInForce(f"{key}: a slot is quarantined in this process; no new sandbox starts")
                            t0 = time.monotonic()
                            sbx = Sandbox.start(key, s.option, s.layout, dc, cfg)
                            r["sandbox_start_s"] = round(time.monotonic() - t0, 3)
                        del dc
                        ex = sbx.exec(code or exec_code(s, ops, expect=expected_bytes(ops, manifest)), exec_timeout_s())
                        res = next((json.loads(x[len(RESULT_TAG):]) for x in ex.stdout.splitlines()
                                    if x.startswith(RESULT_TAG)), None)
                        val = next((json.loads(x[len("ICSA_VAL "):]) for x in ex.stdout.splitlines() if x.startswith("ICSA_VAL ")), None)
                        if code is not None:
                            r["val"] = val
                            if val is None and ex.exit_code == 0:
                                r["errors"].append("the validation script printed no record")
                        if ex.exit_code != 0 or res is None:
                            r["errors"].append(f"exec failed: exit {ex.exit_code}")
                            r["stderr_tail"] = _redact(ex.stderr or "", lt.token)[-1500:]
                        else:
                            r.update(res)
                            short = check_reads(res, ops, manifest)
                            if short:
                                r["errors"] += short
                                r["short_read"] = True
                        meta = sbx.metadata() if hasattr(sbx, "metadata") else {}
                        if meta.get("earlyoom_kills"):       # host infrastructure: this run's result does not count
                            r["earlyoom_kills"] = meta["earlyoom_kills"]
                            r["errors"].append(f"earlyoom killed {len(meta['earlyoom_kills'])} process(es) of this run")
                        elif meta.get("earlyoom_log_readable") is False:
                            r["errors"].append("earlyoom's journal could not be read: whether this run was hit is not known")
                        r["collected"] = sbx.collect(out)
                        _move_perf(out, runs_dir / "perf" / key)
                        if s.option is Option.M and not list((runs_dir / "perf" / key).glob("read_write_perf-*.csv")):
                            r["errors"].append("M run without its oneclient perf CSV")
                    except QuarantineInForce:
                        raise
                    except StartRefused as e:
                        raise NoSandboxStarted(f"{key}: {e}") from e      # before any container: not an attempt, and not a failure to retry
                    except BaseException as e:
                        r["errors"].append(_redact(f"{type(e).__name__}: {e}", lt.token))
                        if sbx is None and getattr(e, "sandbox", None) is not None:
                            _quarantine(r, lt.lease, valid_until, "a failed start left a sandbox behind")
                        if not isinstance(e, Exception):
                            raise
                finally:
                    if sbx is not None:
                        try:
                            sbx.stop()
                        except BaseException as e:
                            r["errors"].append(_redact(f"teardown failed: {type(e).__name__}: {e}", lt.token))
                            _quarantine(r, lt.lease, valid_until, "teardown failed")
                            if not isinstance(e, Exception):
                                raise
                    r["lease_end_utc"] = utc_ms()
        r["onedata_slot"] = lease.final_record()
        r["ok"] = not r["errors"] and "run_start_utc" in r
    except RunRefused as e:
        refused = isinstance(e, (QuarantineInForce, NoSandboxStarted))           # no sandbox started: this attempt leaves no key and no record behind
        raise
    except Exception as e:  # noqa: BLE001 - a failed run is a result, recorded; the ledger records it lost
        r["errors"].append(f"{type(e).__name__}: {e}")
    finally:
        r["errors"] = [_redact(x, *secret)[:800] for x in r["errors"]]
        if refused:
            import shutil
            shutil.rmtree(out, ignore_errors=True)
        else:
            _save_record(out, r, secret)
    return r


def _save_record(out: Path, r: dict, secret: list[str]) -> None:
    tmp = out / "run.json.tmp"
    tmp.write_text(_redact(json.dumps(r, indent=1, default=str), *secret))
    os.replace(tmp, out / "run.json")


def _quarantine(r: dict, slot_lease, valid_until: float, why: str) -> None:
    r["errors"].append(f"{why}: slot quarantined until its teardown is proven")
    r["quarantined"] = True
    with ADMIT:
        QUARANTINED_UNTIL.append(valid_until)
        QUARANTINED_LEASES.append(slot_lease)
    slot_lease.quarantine(valid_until)


def _move_perf(out: Path, dest: Path) -> None:
    """The run's own perf CSVs (M) to perf/<run key>/, where `matcher.perf_events` reads them by sidecar identity."""
    src = out / "oneclient_perf"
    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for f in src.glob("read_write_perf-*.csv"):
            f.rename(dest / f.name)


def run_calibration(plan, claim, ledger: Ledger, required: Required, manifests: dict, cfg, runs_dir: Path, *,
                    pause_file: Path | None = None, execute: Callable = execute_run, log=print, gate: Callable[[], str | None] | None = None,
                    concurrency: int = 1, only: set | None = None) -> str:
    """Pending runs, the replacements of lost runs first (in the plan's order), then the rest in the plan's order; serial by default, at most
    `concurrency` sandboxes at once (capped at the curve's top level). A lost run comes back as a fresh attempt, up to the ledger's MAX_ATTEMPTS,
    first in the next pass. Returns 'done',
    'paused' (the pause file, checked before each new run) or 'stopped' (a quarantine: nothing new starts)."""
    import concurrent.futures as cf
    import threading
    from icsa.scripted.plans import MAX_LEVEL
    if not 1 <= concurrency <= MAX_LEVEL:
        raise ValueError(f"concurrency {concurrency}: 1..{MAX_LEVEL}")
    lock = threading.Lock()
    stop = threading.Event()
    for sid in _started(ledger):                    # interrupted by a crash: lost, and replaced like any failed run
        ledger.mark_lost(sid, "interrupted")

    def one(p) -> None:
        sid = p.scenario.sid
        try:
            r = execute(p, claim, required, manifests[p.scenario.layout], cfg, runs_dir)
        except (QuarantineInForce, NoSandboxStarted) as e:
            with lock:
                ledger.unstart(sid, f"stopped: {e}")        # no sandbox started: no attempt used; the batch stops, the run goes after the look
            stop.set()
            return
        except RunRefused as e:
            with lock:
                ledger.mark_lost(sid, f"refused: {e}")
            stop.set()
            raise
        except BaseException as e:
            with lock:
                ledger.mark_lost(sid, f"{type(e).__name__}")
            stop.set()
            raise
        with lock:
            if r.get("ok"):
                ledger.finish_run(sid)
            else:
                ledger.mark_lost(sid, "; ".join(r.get("errors", []))[:300] or "not ok")
            log(json.dumps({k: r.get(k) for k in ("run_key", "ok", "slot", "run_start_utc", "run_end_utc", "errors")}))
        if r.get("quarantined"):
            stop.set()

    status = "done"
    try:
        with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
            while status == "done" and not (stop.is_set() or QUARANTINED_UNTIL):
                pending = set(ledger.pending())
                todo = [p for p in plan if p.scenario.sid in pending and (only is None or p.scenario.sid in only)]
                redo = set(ledger.lost())
                again = set(ledger.rerun_pending())
                # the replacements of lost runs first, then the old site_g's finished runs again (science, 3 Nov), then every planned run not yet done (amendment 29(g)); plan order within each
                todo.sort(key=lambda p: 0 if p.scenario.sid in redo else 1 if p.scenario.sid in again else 2)
                if not todo:
                    break
                running: set = set()
                for p in todo:
                    while len(running) >= concurrency:          # a free place first: the pause is checked at a boundary
                        done_, running = cf.wait(running, return_when=cf.FIRST_COMPLETED)
                        for f in done_:
                            f.result()
                    if stop.is_set() or QUARANTINED_UNTIL:    # a quarantine stops admission at once
                        status = "stopped"
                        break
                    if pause_file is not None and Path(pause_file).exists():
                        log(f"paused before {p.scenario.sid}: {pause_file} exists")
                        status = "paused"
                        break
                    why = gate() if gate else None
                    if why:
                        log(f"paused before {p.scenario.sid}: {why}")
                        status = "paused"
                        break
                    with lock:
                        ledger.begin_run(p.scenario.sid)
                    running.add(pool.submit(one, p))
                for f in cf.as_completed(running):
                    f.result()
        if (stop.is_set() or QUARANTINED_UNTIL) and status == "done":
            status = "stopped"
        return status
    finally:
        hold_quarantines()


def seam_sids(plan) -> set[str]:
    """The seam test's cells: the first planned run of each option x layout (in the plan's order)."""
    first: dict = {}
    for p in plan:
        first.setdefault((p.scenario.option, p.scenario.layout), p.scenario.sid)
    return set(first.values())


def _started(ledger: Ledger) -> list[str]:
    d = ledger._read()
    return [s for s, v in d.get("state", {}).items() if v == "started"]


# ---- the raw-read timing (parent's GO, 1 Nov 23:10Z): n I01 files per option, the calibration's own reads ---------
def measure(out: Path, image: str, n: int = 100, options=(Option.T, Option.D, Option.M), layout: Layout = Layout.S1) -> dict:
    from icsa import grid
    from icsa.harness.config import load_config
    from icsa.harness.real_sandbox import sandbox_config
    from icsa.instances import load as IL
    from icsa.sandbox.config import pin_image

    from .matrix import PlannedRun
    from .scenarios import Fault, make_scenario
    from .units import FileEntry, _dataset_spans
    rec = next(r for r in IL.load_instances()["instances"] if r.get("calibration"))
    units, files = {}, []
    if layout is Layout.S1:
        root = Path("/mnt/volume2/icsa-2027/s1z")
        for nm in IL.s1_files(rec)[:n]:
            d = grid.day_index(dt.date(int(nm[4:8]), int(nm[8:10]), int(nm[10:12])))
            (_, a, b), = _dataset_spans(root / nm, "analysed_sst")
            units[d] = (nm, a, b)
            files.append(FileEntry(nm, f"s1z/{nm}", (root / nm).stat().st_size))
    else:                                       # S2: the first n required days' chunks of the one file
        f2 = Path("/mnt/volume2/icsa-2027/s2z/sst_s2.nc")
        want = set(int(d) for d in sorted(IL.required_day_indices(rec))[:n])
        units = {d: ("sst_s2.nc", a, b) for d, a, b in _dataset_spans(f2, "analysed_sst") if d in want}
        files.append(FileEntry("sst_s2.nc", "s2z/sst_s2.nc", f2.stat().st_size))
    man = Manifest(layout, tuple(files), units)
    req = Required.from_days(sorted(units), [])
    cfg = sandbox_config(image, pin_image(image), sandbox_limits=load_config().sandbox_limits)
    stamp = time.strftime("%H%M%S", time.gmtime())
    res = {"instance": rec["instance"]["instance_id"], "layout": layout.value, "n_units": n, "image": image, "runs": []}
    (out / "runs").mkdir(parents=True, exist_ok=True)
    try:
        return _measure_runs(res, options, layout, req, man, cfg, out, stamp)
    finally:
        hold_quarantines()


def _measure_runs(res, options, layout, req, man, cfg, out, stamp) -> dict:
    from .matrix import PlannedRun
    from .scenarios import Fault, make_scenario
    for i, o in enumerate(options):
        s = make_scenario(Fault.NONE, layout, o, Condition.COLD, 0, 0)
        r = execute_run(PlannedRun(i, s, None), None, req, man, cfg, out / "runs",
                        key=f"{PREFIX}measure-{o.value}{layout.value}-{stamp}")
        span = (dt.datetime.fromisoformat(r["run_end_utc"]) - dt.datetime.fromisoformat(r["run_start_utc"])).total_seconds() \
            if r.get("ok") else None
        res["runs"].append({"option": o.value, "run_key": r["run_key"], "ok": r.get("ok"), "errors": r.get("errors"),
                            "sandbox_start_s": r.get("sandbox_start_s"), "read_s": span, "bytes": r.get("bytes"),
                            "s_per_unit": round(span / res["n_units"], 4) if span else None, "slot": r.get("slot")})
        print(json.dumps(res["runs"][-1]), flush=True)
        if r.get("quarantined"):
            break
    (out / f"MEASURE-{layout.value}-{stamp}.json").write_text(json.dumps(res, indent=1))
    return res


# ---- pull (read-only kubectl, filtered at the source) -----------------------------------------------------------
AUDIT_DIR, AUDIT_NAME = "/var/log/op_worker", "file_access_audit.log"
TRAEFIK_DIR, TRAEFIK_NAME = "/data", "access.log"
_OP_EXEC = "kubectl --kubeconfig ~/.kube/site_g-config -n oneprovider-site_g exec oneprovider-0 --"
_TR_EXEC = "kubectl --kubeconfig ~/.kube/site_g-config -n traefik exec deploy/traefik -c traefik --"
_RC = re.compile(r"^ICSA_PULL_RC=(\d+)$")
_GZIP_BAD = "ICSA_GZIP_BAD"
PULL_TIMEOUT_S = 600


TRAEFIK_KEEP = 16           # site_g's Traefik keeps this many rotated files of 1 GiB (science, #2, 2 Nov); the next one drops the oldest
TRAEFIK_ALARM_AT = 12       # rotated files no pull has read, at which the watcher stops dispatch: 4 GiB of room; a pull clears it
_ROTATED = re.compile(r"\.(\d{8}T\d{6}Z)(?:\.gz)?$")
_NO_READ = (".zst", ".bz2", ".xz", ".lz4", ".zip")


def _rotated_at(name: str) -> float | None:
    """access.log.20261101T210100Z[.gz]: when it was rotated, epoch s; None if the name does not say."""
    m = _ROTATED.search(name)
    if not m:
        return None
    try:
        return dt.datetime.strptime(m[1], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
    except ValueError:
        return None


class RotatedLog(RuntimeError):
    """A rotated sibling of the audit log exists on site_g: a pull of the live file alone would lose lines, and scoring would read
    their absence as unread days. It does not rotate on site_g today, so this needs a person, never a silent read."""


def _listing(run: Callable, dsk: Path, env: dict, ex: str, d: str, name: str) -> list[str]:
    """The log's name and its siblings' names, live file first."""
    p = run(["bash", str(dsk), f"{ex} sh -c 'ls -1 {d}'"], capture_output=True, text=True, timeout=PULL_TIMEOUT_S, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"pull: cannot list {d}: exit {p.returncode}: {p.stderr[-300:]}")
    names = p.stdout.split()
    if name not in names:
        raise RuntimeError(f"pull: {d}/{name} is not there: is the log on, and did it move? Seen: {names[:10]}")
    return [name] + sorted(n for n in names if n != name and n.startswith(name))


def _pull_one(run: Callable, dsk: Path, env: dict, name: str, ex: str, grep: str) -> list[str]:
    """One filtered read. grep's exit status comes back on a last line of its own: 1 (no line matched) and a dead transport
    both exit 1 otherwise, and a failed read must never look like an empty log."""
    p = run(["bash", str(dsk), f'{ex} sh -c "{grep}; echo ICSA_PULL_RC=\\$?"'], capture_output=True, text=True,
            timeout=PULL_TIMEOUT_S, env=env)
    lines = p.stdout.splitlines()
    m = _RC.match(lines[-1]) if lines else None
    if m is None:
        raise RuntimeError(f"pull {name}: no exit status from the remote read (exit {p.returncode}): {p.stderr[-300:]}")
    if m.group(1) not in ("0", "1"):             # grep: 1 = no line matched
        raise RuntimeError(f"pull {name}: grep exit {m.group(1)}: {p.stderr[-300:]}")
    if _GZIP_BAD in lines:
        raise RuntimeError(f"pull {name}: a compressed sibling does not decompress: its lines would read as unread days")
    return lines[:-1]


def _read_traefik(run: Callable, dsk: Path, env: dict, files: list[str], key_prefix: str) -> list[str]:
    """Every line under our run keys from the live file and every sibling: a run can span a rotation."""
    bad = [f for f in files if f.endswith(_NO_READ)]
    if bad:
        raise RuntimeError(f"pull traefik.jsonl: sibling(s) in a format this cannot read: {bad}")
    plain = [f"{TRAEFIK_DIR}/{f}" for f in files if not f.endswith(".gz")]
    lines = _pull_one(run, dsk, env, "traefik.jsonl", _TR_EXEC, f"grep -hF {key_prefix} {' '.join(plain)}")
    for f in files:
        if f.endswith(".gz"):
            g = f"{TRAEFIK_DIR}/{f}"
            lines += _pull_one(run, dsk, env, "traefik.jsonl", _TR_EXEC,
                               f"if gzip -t {g}; then gzip -dc {g} | grep -hF {key_prefix}; else echo {_GZIP_BAD}; fi")
    return [x for x in lines if x.startswith("{")]


def traefik_alarm(files: list[str], last_pull: float | None) -> list[str]:
    """Why the kept Traefik logs need attention, or []. Traefik drops its oldest file as it rotates, which is routine for a file
    a pull has read: a sibling named access.log.<UTC> holds nothing newer than that time. Lines are lost only when a file not yet
    pulled reaches the front, so what counts is how many kept files were rotated after the last pull (`last_pull`, epoch s; None:
    all of them). A name without a readable time cannot be placed: that needs a person."""
    siblings = files[1:]                         # the first is the live file
    out = []
    unnamed = [f for f in siblings if _rotated_at(f) is None]
    if unnamed:
        out.append(f"Traefik log(s) with no readable rotation time, so their lines cannot be placed: {unnamed[:3]}")
    fresh = [f for f in siblings if last_pull is None or (t := _rotated_at(f)) is None or t > last_pull]
    if len(fresh) >= TRAEFIK_ALARM_AT:
        out.append(f"{len(fresh)} of the {TRAEFIK_KEEP} kept Traefik logs were rotated after the last pull: pull now. "
                   f"At {TRAEFIK_KEEP} the next rotation drops lines no pull has read")
    return out


LOGCHECK_MAX_AGE_S = 900.0        # three of a 5-minute watcher's beats missed: past this a heartbeat says nothing about the logs


def write_heartbeat(path: Path, got: dict) -> None:
    """What `logcheck --heartbeat` leaves for `run`, which may not be on the host holding site_g's key (science, #2, 2 Nov 08:15Z)."""
    tmp = Path(path).with_name(Path(path).name + ".tmp")
    tmp.write_text(json.dumps({"checked_epoch": time.time(), "checked_utc": utc_ms(), "host": socket.gethostname(), "alarms": got["alarms"],
                               "n_siblings": got.get("n_siblings")}))
    os.replace(tmp, path)


def heartbeat_problem(path: Path, now: float | None = None, max_age_s: float = LOGCHECK_MAX_AGE_S) -> str | None:
    """Why a heartbeat does not let a new run start, or None. Missing, unreadable or old is no answer, so it holds, as an alarm does."""
    try:
        d = json.loads(Path(path).read_text())
        age = (time.time() if now is None else now) - float(d["checked_epoch"])
        alarms = d["alarms"]
    except FileNotFoundError:
        return f"no kept-log heartbeat at {path}: is the watcher (logcheck --heartbeat) running?"
    except (OSError, ValueError, KeyError, TypeError) as e:
        return f"the kept-log heartbeat {path} cannot be read ({type(e).__name__})"
    if age > max_age_s:
        return f"the kept-log heartbeat {path} is {age:.0f} s old (limit {max_age_s:.0f}): is the watcher running?"
    if alarms:
        return f"the kept-log check alarms: {alarms}"
    return None


def _note_logcheck(out: Path, entry: dict) -> None:
    with open(out / "LOGCHECK.jsonl", "a") as fh:
        fh.write(json.dumps({"utc": utc_ms(), **entry}) + "\n")


def _store_capture(out: Path, name: str, lines: list[str], pulled_utc: str, files: list[str] | None = None,
                   scope: Callable | None = None) -> None:
    """Never overwrite a capture (science, #2, 2 Nov): this pull's bytes are kept under pulls/ by hash, the capture only grows.
    A line counts as often as any one pull saw it, so identical lines keep their count and a re-pull adds only what is new;
    lines that have since gone from the source (a truncated log) stay. The number the source lost since the previous pull is
    noted (`n_gone`): whatever it wrote after that pull and lost before this one is gone unseen, so `capture_gaps` reads that
    span as not covered. A loss counts once: the next pull compares with this one, not with the capture.
    `scope`: which of the capture's lines this pull could have seen, for a read filtered more narrowly than the capture."""
    pulls = out / "pulls"
    pulls.mkdir(exist_ok=True)
    log = out / "PULLS.jsonl"
    cur = out / name

    def keep(raw: bytes) -> str:
        sha = hashlib.sha256(raw).hexdigest()
        f = pulls / f"{name}.{sha[:12]}"
        if not f.exists():
            tmp = f.with_name(f.name + ".tmp")
            tmp.write_bytes(raw)
            os.replace(tmp, f)
        return sha

    def note(**e) -> None:
        with log.open("a") as fh:
            fh.write(json.dumps({"name": name, **e}) + "\n")
    known = log.exists() and any(json.loads(x)["name"] == name for x in log.read_text().splitlines())
    if cur.exists() and not known:               # a capture from before this log: it goes first, verbatim
        raw = cur.read_bytes()
        mtime = dt.datetime.fromtimestamp(cur.stat().st_mtime, dt.timezone.utc).isoformat(timespec="milliseconds")
        note(sha256=keep(raw), n_lines=len(raw.splitlines()), pulled_utc=mtime, origin="existing capture")
    rows = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    last = next((r for r in reversed(rows) if r["name"] == name), None)
    prev = (pulls / f"{name}.{last['sha256'][:12]}").read_text().splitlines() if last else []   # the source as last read
    text = "".join(x + "\n" for x in lines)
    sha = keep(text.encode())
    old = cur.read_text() if cur.exists() else ""
    have = collections.Counter(old.splitlines())
    new = []
    for x in lines:
        if have[x] > 0:
            have[x] -= 1
        else:
            new.append(x)
    with cur.open("a") as fh:
        if old and not old.endswith("\n"):
            fh.write("\n")
        fh.write("".join(x + "\n" for x in new))
    gone_lines = collections.Counter(prev) - collections.Counter(lines)
    if prev and gone_lines.get(prev[-1]) and any(y != prev[-1] and y.startswith(prev[-1]) and lines.count(y) > prev.count(y) for y in lines):
        gone_lines[prev[-1]] -= 1       # the last line of the last read, cut off while being written, is complete now: not a loss
    gone = sum(c for x, c in gone_lines.items() if scope is None or scope(x))
    note(sha256=sha, n_lines=len(lines), n_new=len(new), n_gone=gone, pulled_utc=pulled_utc, origin="pull",
         **({"files": files} if files else {}))


def pull_logs(out: Path, users: list[str], key_prefix: str, dsk: Path = REPO / "day0" / "scripts" / "dsk.sh",
              run: Callable = subprocess.run) -> dict:
    """Our lines from site_g, filtered at the source."""
    if not users or not all(re.fullmatch(r"[A-Za-z0-9]+", u) for u in users):
        raise ValueError("pull needs our slot users' ids (alphanumeric)")
    if not RUN_KEY_RE.match(key_prefix + "0000-x") or not key_prefix.startswith(PREFIX):
        raise ValueError(f"bad run-key prefix {key_prefix!r}")
    env = {**os.environ, "DSK_TIMEOUT": str(PULL_TIMEOUT_S - 20)}
    audit_files = _listing(run, dsk, env, _OP_EXEC, AUDIT_DIR, AUDIT_NAME)
    if len(audit_files) > 1:
        raise RotatedLog(f"rotated sibling(s) of {AUDIT_DIR}/{AUDIT_NAME}: {audit_files[1:]}. Lines in them would read as "
                         "unread days; collect them by hand before scoring")
    files = _listing(run, dsk, env, _TR_EXEC, TRAEFIK_DIR, TRAEFIK_NAME)
    alt = "|".join(sorted(set(users)))
    pulled = utc_ms()          # taken before the reads: a line written after this may be missing, and `score` allows for it
    audit = _pull_one(run, dsk, env, "audit.log", _OP_EXEC, f"grep -E 'user: ({alt});' {AUDIT_DIR}/{AUDIT_NAME}")
    traefik = _read_traefik(run, dsk, env, files, key_prefix)
    after = _listing(run, dsk, env, _TR_EXEC, TRAEFIK_DIR, TRAEFIK_NAME)
    if after != files:
        raise RuntimeError(f"pull: Traefik rotated during the pull ({sorted(set(after) ^ set(files))}): nothing was stored, run it again")
    alarms = traefik_alarm(files, dt.datetime.fromisoformat(pulled).timestamp())    # this pull has read them all
    _store_capture(out, "audit.log", audit, pulled)    # every read succeeded: only now does either capture change
    _store_capture(out, "traefik.jsonl", traefik, pulled, files=files)
    for a in alarms:
        print(f"ALARM: {a}", file=sys.stderr)
    return {"audit.log": len(audit), "traefik.jsonl": len(traefik), "alarms": alarms}


def log_check(out: Path, dsk: Path = REPO / "day0" / "scripts" / "dsk.sh", run: Callable = subprocess.run) -> dict:
    """For a watcher: Traefik's kept logs against the last pull, read-only. `alarms` non-empty means stop dispatch and pull."""
    from .records.base import Record
    env = {**os.environ, "DSK_TIMEOUT": "60"}
    files = _listing(run, dsk, env, _TR_EXEC, TRAEFIK_DIR, TRAEFIK_NAME)
    last = capture_times(out).get(Record.TRAEFIK)
    return {"n_siblings": len(files) - 1, "keep": TRAEFIK_KEEP, "alarm_at": TRAEFIK_ALARM_AT, "last_pull_epoch": last,
            "alarms": traefik_alarm(files, last)}


def capture_gaps(out: Path) -> dict:
    """{Record.AUDIT: [(from, to), epoch s]}: spans between two pulls where the audit log lost lines the capture held, so lines
    written in that span may be gone unseen. A run overlapping one is not observed on the audit record. Audit only: it should
    never lose a line, and nothing else can show one was lost. Traefik drops whole old files as routine (its `n_gone` is noted,
    no more), and each run's gate log proves that run's lines, more strongly than a span over every run could."""
    from .records.base import Record
    log = out / "PULLS.jsonl"
    rows = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    seq = [r for r in rows if r["name"] == "audit.log"]
    ep = lambda r: dt.datetime.fromisoformat(r["pulled_utc"]).timestamp()     # noqa: E731
    spans = [(ep(a), ep(b)) for a, b in zip(seq, seq[1:]) if b.get("n_gone")]
    return {Record.AUDIT: spans} if spans else {}


def capture_times(out: Path) -> dict:
    """{Record: when its capture last read the source, epoch s}, for `score`'s coverage check. The latest pull in PULLS.jsonl,
    or the file's modification time for a capture from before that log."""
    from .records.base import Record
    got = {}
    log = out / "PULLS.jsonl"
    rows = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
    for rec, name in ((Record.AUDIT, "audit.log"), (Record.TRAEFIK, "traefik.jsonl")):
        ts = [dt.datetime.fromisoformat(r["pulled_utc"]).timestamp() for r in rows if r["name"] == name]
        if ts:
            got[rec] = max(ts)
        elif (out / name).exists():
            got[rec] = (out / name).stat().st_mtime
    return got


# ---- score -------------------------------------------------------------------------------------------------------
def _attempts(claim, p, runs_dir: Path) -> list[dict]:
    """The run records of a planned run's attempts, in order."""
    out = []
    for k in attempt_keys(claim.sha, p.order, p.scenario):
        f = runs_dir / k / "run.json"
        if f.exists():
            out.append(json.loads(f.read_text()))
    return out


def gate_forwarded(path: Path) -> int | None:
    """Requests the run's own gate forwarded to the provider and got an answer to; None if there is no readable gate log.
    Each must be a Traefik line under the run's key: the gate is what adds X-ICSA-Run, so a shortfall is a lost record."""
    if not path.exists():
        return None
    n = 0
    try:
        for line in path.read_text().splitlines():
            g = json.loads(line)
            if (g.get("decision") == "allow" and g.get("status") is not None
                    and str(g.get("path", "")).startswith("/api/v3/oneprovider/")):
                n += 1
    except (ValueError, AttributeError):
        return None
    return n


def not_observed(rec, ev: list, o, run_end: float, gate: int | None, pulled_at: float | None) -> str | None:
    """Why this record does not show this run, or None. The detector would read a record's silence as "nothing was read",
    which is a flag and so a detection (or an alarm), from no evidence (science, #2, 2 Nov: must not ship)."""
    from .records.base import Record
    if pulled_at is not None and run_end + PERF_MARGIN_S > pulled_at:
        return f"not_observed: the {rec.value} capture was taken before the run ended"
    if not ev:
        return f"not_observed: no {rec.value} line attributed to the run"
    if rec is Record.TRAEFIK:
        if gate is None:
            return "not_observed: no gate log, so the Traefik record's completeness cannot be established"
        if gate != len(ev):
            return f"not_observed: Traefik holds {len(ev)} line(s) under the run key, the gate forwarded {gate}"
    if o.n_unresolved:
        return f"not_observed: {o.n_unresolved} response(s) unresolved: their bytes cannot be credited"
    if not o.n_used:
        return f"not_observed: no read in the {rec.value} lines attributed to the run"
    return None


KEPT_RERUN_REASON = "science ruling 3 Nov: the old site_g's finished run is run again on the final head; its record is kept and reported apart"
RERUN_RULE = ("amendment 30(j): the old site_g's earlier runs (13: every done run whose latest record carries no tags) are all run again on the new VM and the final head, after the replacements, "
              "whatever they showed; their records are kept and reported apart (h3_table_old_site_g_apart), so no selection arises")


def mark_kept_for_rerun(plan, claim, ledger: Ledger, runs_dir: Path) -> list[str]:
    """Every done run whose latest record carries no tags of its own (written before runs carried them: the old site_g's) goes back for a rerun, whatever it showed.
    Idempotent: a run already put back is not done, and a finished rerun carries its own tags. The sealed plan is not touched; nothing under runs_dir is."""
    marked = []
    done = {s for s, v in ledger._read().get("state", {}).items() if v == "done"}
    for p in plan:
        sid = p.scenario.sid
        recs = _attempts(claim, p, runs_dir)
        if sid in done and recs and not recs[-1].get("tags"):
            ledger.rerun(sid, KEPT_RERUN_REASON)
            marked.append(sid)
    return marked


def choose_record(recs: list[dict], sid: str, done: set | None, apart: set | None = None) -> dict | None:
    """The record a run is scored from. Normally the latest ok attempt, if the ledger confirms the run done. In the apart pass (`apart`: the sids put back for a
    rerun) only those runs, from their EARLIEST ok record, which is the old site_g's kept one; the others are not scored there."""
    if apart is not None:
        return next((r for r in recs if r.get("ok")), None) if sid in apart else None
    return next((r for r in reversed(recs) if r.get("ok") and (done is None or sid in done)), None)


def score(plan, claim, required: Required, manifests: dict, runs_dir: Path, audit_text: str, traefik_text: str,
          slot_map: dict, kp, done: set | None = None, *, pulled_at: dict | None = None, gaps: dict | None = None,
          diag: dict | None = None, apart: set | None = None) -> list:
    """FaultRuns for fidelity, per run and per record of its option; attribution by slot user, run key and the run's own
    perf CSV only (its rows inside the run's window: a warm_buffer pre-read is outside it). Only runs the ledger confirms
    as done are scored (`done`): a run whose record says ok but whose ledger entry is lost is lost.

    Attribution uses EVERY run's window, failed attempts and lost runs included: a failed run's reads must not move to a
    neighbour (science, #2, 2 Nov). A failed run's window is its widest known span (its lease; to the token's expiry if it
    crashed and left no end). A same-slot neighbour inside the margin is then ambiguous: invalid, counted. An attempt that left
    only its directory (runs older than the early record) has no known slot: slot leases are exclusive and it never released
    its own, so on a neighbour's slot it can only have started after that neighbour's lease ended, and the neighbour is
    affected only if that lease ended inside its margin and the lost attempt had begun by then. An invalid run gets
    `excluded_reason`; `diag`, if given, collects the lines nothing can claim. `pulled_at` ({Record: epoch s}) is when each
    capture last read its source; `gaps` ({Record: [(from, to)]}) are the spans where its source lost lines (`capture_gaps`)."""
    from .detector import DetectorSpec, detect
    from .fidelity import FaultRun, content_summary
    from .matcher import RunInterval, RunWindow, attribute_audit_by_slot, attribute_traefik_by_header, perf_events
    from .observability import RECORDS_OF
    from .records.audit import parse_audit, salvage
    from .records.base import Record
    from .records.traefik import parse_traefik
    from .scenarios import injection

    ep = lambda iso: dt.datetime.fromisoformat(iso).timestamp()     # noqa: E731
    ok, failed, unrecorded = {}, [], []
    for p in plan:
        sid = p.scenario.sid
        recs = _attempts(claim, p, runs_dir)
        chosen = choose_record(recs, sid, done, apart)
        if chosen is not None:
            ok[sid] = (p, chosen)
        failed += [r for r in recs if r is not chosen]
        for k in attempt_keys(claim.sha, p.order, p.scenario):
            d = runs_dir / k
            if d.is_dir() and not (d / "run.json").exists():     # mkdir comes first: no directory, nothing of it ever ran
                unrecorded.append((p.scenario.option.value, None if any(d.iterdir()) else d.stat().st_mtime, k))

    def span(r: dict) -> tuple[float, float] | None:
        """A record that did not finish as a scored run: when it may have read, widest first. None: it never held a slot."""
        if not r.get("slot"):
            return None
        starts = [ep(r[k]) for k in ("lease_start_utc", "warm_start_utc", "run_start_utc") if r.get(k)]
        ends = [ep(r[k]) for k in ("lease_end_utc", "run_end_utc") if r.get(k)]
        if not starts:
            raise ValueError(f"{r.get('run_key')}: a record with a slot and no start time")
        if ends:
            return min(starts), max(ends)
        return min(starts), ep(r["token_valid_until_utc"]) if r.get("token_valid_until_utc") else math.inf
    intervals = [RunInterval(r["run_key"], r["option"], r["slot"], ep(r["run_start_utc"]), ep(r["run_end_utc"]))
                 for _, r in ok.values()]
    for r in failed:
        w = span(r)
        if w is not None:
            intervals.append(RunInterval(r["run_key"], r["option"], r["slot"], *w))
    windows = [RunWindow(i.run_key, i.start, i.end) for i in intervals]
    parsed_a, parsed_t = parse_audit(audit_text), parse_traefik(traefik_text)
    whole_lines = audit_text.splitlines()                    # a bad line that is the start of a good one is that line, cut by a pull
    bad_a = [salvage(x) for x in parsed_a.bad_lines if not any(g != x and g.startswith(x) for g in whole_lines)]
    att_a = attribute_audit_by_slot(parsed_a.events, intervals, slot_map, kp=kp)
    att_t = attribute_traefik_by_header(parsed_t.events, windows, kp=kp)
    if diag is not None:
        diag.update(traefik_lines_without_key=att_t.n_unattributable, traefik_lines_unknown_key=att_t.n_unknown_key,
                    audit_bad_lines=parsed_a.n_bad, traefik_bad_lines=parsed_t.n_bad,
                    audit_ambiguous_events=sum(att_a[r["run_key"]].n_ambiguous for _, r in ok.values()),
                    attempts_without_record=len(unrecorded))

    def touched_by_bad_line(r) -> str | None:
        """A line the format did not match may be this run's read, if neither its user nor its time rules that out."""
        user = slot_map[r["slot"]].user
        a, b = ep(r["run_start_utc"]) - PERF_MARGIN_S, ep(r["run_end_utc"]) + PERF_MARGIN_S
        n = sum((u is None or u == user) and (t is None or a <= t <= b) for t, u in bad_a)
        return f"{n} malformed audit line(s) may be this run's reads" if n else None

    def touched_by_unrecorded(s, r) -> str | None:
        end = ep(r["run_end_utc"]) + PERF_MARGIN_S
        lease_end = ep(r["lease_end_utc"]) if r.get("lease_end_utc") else ep(r["run_end_utc"])
        if lease_end > end:        # the slot was still ours past the margin: nothing else's read can land inside it
            return None
        for opt, t, k in unrecorded:
            if opt == s.option.value and (t is None or t <= end):   # t only bounds it below: it may have waited for this slot
                return f"attempt {k} left no record and may share this slot inside the margin"
        return None
    out = []
    for sid, (p, r) in ok.items():
        s, key = p.scenario, r["run_key"]
        inj = injection(s, required)
        man = manifests[s.layout]
        short = check_reads(r, read_ops(s, required, man), man)
        for rec in RECORDS_OF[s.option]:
            excluded = short[0] if short else None
            if rec is Record.AUDIT:
                a = att_a[key]
                ev = a.events
                excluded = excluded or a.excluded_reason or touched_by_unrecorded(s, r) or touched_by_bad_line(r)
            elif rec is Record.TRAEFIK:
                ev = att_t.by_run.get(key, [])
            else:
                w0, w1 = ep(r["run_start_utc"]) - PERF_MARGIN_S, ep(r["run_end_utc"]) + PERF_MARGIN_S
                n_bad: list = []
                try:
                    ev = [e for e in perf_events(runs_dir / "perf", key, n_bad=n_bad) if e.ts is not None and w0 <= e.ts <= w1]
                except FileNotFoundError:
                    ev = []
                if sum(n_bad):             # its own sidecar's file: an unreadable row may be one of its reads
                    excluded = excluded or f"{sum(n_bad)} malformed perf row(s) may be this run's reads"
            o = detect(ev, required, man, DetectorSpec(rec))
            gate = gate_forwarded(runs_dir / key / "gate_requests.jsonl") if rec is Record.TRAEFIK else None
            if rec is Record.TRAEFIK and diag is not None:       # amendment 17(c), check (i): the gate log against Traefik's, on every such run
                from .gatecheck import compare, gate_text_of
                diag.setdefault("gate_vs_traefik", []).append({"option": s.option.value, "layout": s.layout.value, "sid": sid,
                                                               **compare(key, gate_text_of(runs_dir / key), ev, required, man)})
            why = not_observed(rec, ev, o, ep(r["run_end_utc"]), gate, (pulled_at or {}).get(rec))
            for g0, g1 in (gaps or {}).get(rec, ()):
                if ep(r["run_start_utc"]) <= g1 and ep(r["run_end_utc"]) + PERF_MARGIN_S >= g0:
                    why = why or f"not_observed: the {rec.value} log lost lines between two pulls, over this run's window"
            out.append(FaultRun(s, rec, inj, None if why and not excluded else o, excluded_reason=excluded or why,
                                content=content_summary(ev), matrix=claim, masking=p.masking))
    return out


def images_of(plan, claim, runs_dir: Path, out: Path) -> dict:
    """{sid: {image_id, image_layers_sha256}} from each run's record, else from IMAGES.json's "runs" ({run key: {...}},
    for records written before runs carried their image: the seam test's)."""
    extra = json.loads((out / "IMAGES.json").read_text()).get("runs", {}) if (out / "IMAGES.json").exists() else {}
    got = {}
    for p in plan:
        recs = _attempts(claim, p, runs_dir)
        if recs:
            r = recs[-1]
            got[p.scenario.sid] = ({"image_id": r["image_id"], "image_layers_sha256": r.get("image_layers_sha256")}
                                   if r.get("image_id") else extra.get(r["run_key"], {}))
    return got


TAG_FIELDS = ("host", "data_path", "traefik_setting", "tag_source")
OWN_RECORD = "the run's own record"      # tag_source of a run that carries its tags itself; any other source wrote them after the run (amendment 20(e))


def tags_of(plan, claim, runs_dir: Path, out: Path) -> dict:
    """{sid: {host, data_path, traefik_setting, tag_source}} from each run's record, else from RUN_TAGS.json's "runs" ({run key:
    {...}}, for records written before runs carried their tags: those entries say where the tags came from)."""
    extra = json.loads((out / "RUN_TAGS.json").read_text()).get("runs", {}) if (out / "RUN_TAGS.json").exists() else {}
    got = {}
    for p in plan:
        recs = _attempts(claim, p, runs_dir)
        if recs:
            r = recs[-1]
            got[p.scenario.sid] = {**r["tags"], "tag_source": OWN_RECORD} if r.get("tags") else extra.get(r["run_key"], {})
    return got


def tagged_after_the_run(tags: dict) -> list[str]:
    """The sids whose tags were written after their runs (a RUN_TAGS.json entry): amendment 20(e)'s kept runs of the old site_g, which every cell is
    reported with and without. A run with no tag at all is in neither this list nor the tagged ones: `untagged` says so, since it would otherwise stay
    in the table "without" by silence."""
    return sorted(sid for sid, t in tags.items() if t.get("tag_source") and t["tag_source"] != OWN_RECORD)


def untagged(tags: dict) -> list[str]:
    return sorted(sid for sid, t in tags.items() if not t.get("tag_source"))


def h3_with_and_without(runs, *, claim, lost_sids, tags: dict, **kw):
    """(the H3 table of every run, the same table without the runs tagged after the fact or None when there are none, those runs' sids).
    Without them a cell that had one holds a withheld run: its numbers are the others', its status is `incomplete` (20(b): a verdict needs the whole
    allocation), and `n_withheld_*` says how many are left out."""
    from .fidelity import h3_table
    late = tagged_after_the_run(tags)
    full = h3_table(runs, claim=claim, lost_sids=lost_sids, **kw)
    if not late:
        return full, None, late
    gone = set(late)
    return full, h3_table([r for r in runs if r.scenario.sid not in gone], claim=claim, lost_sids=lost_sids, withheld=late, **kw), late


def write_rows(runs, claim, ledger: Ledger, instance_id: str, out: Path, images: dict | None = None,
               tags: dict | None = None) -> None:
    from .fidelity import adapter_rows
    images = images or {}
    tags = tags or {}
    (out / "rows.jsonl").write_text("".join(json.dumps(r.platform_record() | {"sid": r.scenario.sid,
                                                                                "record": r.record.value,
                                                                                **{f: images.get(r.scenario.sid, {}).get(f)
                                                                                   for f in ("image_id",
                                                                                             "image_layers_sha256")},
                                                                                **{f: tags.get(r.scenario.sid, {}).get(f)
                                                                                   for f in TAG_FIELDS}})
                                            + "\n" for r in runs))
    (out / "adapter_rows.jsonl").write_text("".join(json.dumps({"run": a.run.key(), "block": a.block,
                                                                 "platform_record": a.platform_record}) + "\n"
                                                    for a in adapter_rows(runs, instance_id)))
    h3, without, _ = h3_with_and_without(runs, claim=claim, lost_sids=ledger.lost(), tags=tags)
    h3.to_csv(out / "h3_table.csv", index=False)
    h3.to_json(out / "h3_table.json", orient="records")      # what the dossier's criterion 4 reads (`fault_cells`)
    if without is not None:                                   # amendment 20(e): every cell with and without the runs of the old site_g, whose tags were written after them
        without.to_csv(out / "h3_table_without_old_site_g.csv", index=False)
        without.to_json(out / "h3_table_without_old_site_g.json", orient="records")


# ---- CLI ---------------------------------------------------------------------------------------------------------
def _calibration_instance() -> tuple[str, Required]:
    from icsa.instances import load as IL

    from .masking import _required_of
    recs = [r for r in IL.load_instances()["instances"] if r.get("calibration")]
    if len(recs) != 1:
        raise SystemExit(f"expected exactly one instance flagged calibration, got {len(recs)}")
    return recs[0]["instance"]["instance_id"], _required_of(recs[0])


IDS = Path("/mnt/volume2/icsa-2027/layout/ids.json")     # #76 lane, read-only REST listing of site_g, 20:57-20:59Z


def load_ids(path: Path = IDS) -> tuple[dict, str]:
    """{rel path: REST id} from the full index's ids.json (static metadata, never a run's lines), its sha256 checked
    against PROVENANCE.json beside it. Returns (map, sha256)."""
    import hashlib
    raw = Path(path).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    want = json.loads((Path(path).parent / "PROVENANCE.json").read_text())["sha256"][Path(path).name]
    if sha != want:
        raise SystemExit(f"{path}: sha256 {sha[:12]} differs from PROVENANCE.json's {want[:12]}")
    return {rel: i for i, rel in json.loads(raw).items()}, sha


def _manifests(ids_path: Path) -> tuple[dict, str]:
    from .units import build_s1_manifest, build_s2_manifest
    by_rel, sha = load_ids(ids_path)
    s1_ids = {rel.split("/", 1)[1]: i for rel, i in by_rel.items() if rel.startswith("s1z/")}
    s1 = build_s1_manifest(Path("/mnt/volume2/icsa-2027/s1z"), "s1z", ids=s1_ids)
    s2 = build_s2_manifest(Path("/mnt/volume2/icsa-2027/s2z/sst_s2.nc"), "s2z/sst_s2.nc", object_id=by_rel.get("s2z/sst_s2.nc"))
    missing = [f.name for f in s1.files if not f.object_id] + ([] if s2.files[0].object_id else ["sst_s2.nc"])
    if missing:
        raise SystemExit(f"{len(missing)} file(s) without a REST id (Traefik attribution to files needs them), "
                         f"first {missing[:3]}")
    return {Layout.S1: s1, Layout.S2: s2}, sha


def main(argv=None) -> None:
    import pickle

    from icsa.sandbox.termination import exit_on_sigterm
    exit_on_sigterm()     # a SIGTERM is an orderly exit: the sandboxes are stopped in order, in-flight runs end up lost
    from .matrix import calibration_plan
    ap = argparse.ArgumentParser(prog="python -m icsa.faults.calibrate")
    ap.add_argument("command", choices=["plan", "run", "pull", "score", "measure", "verdict", "logcheck"])
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--layout", default="S1", choices=["S1", "S2"])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--ids", type=Path, default=IDS)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--seam", action="store_true", help="only the first planned run of each option x layout, serially")
    ap.add_argument("--image")
    ap.add_argument("--pause-file", type=Path)
    ap.add_argument("--traefik-setting", help="run: which site_g Traefik setting this run is under; stamped on every run record")
    ap.add_argument("--data-path", help="run: internal or public path to site_g; stamped on every run record")
    ap.add_argument("--partial", action="store_true", help="score while runs are still pending: for a report, never a verdict")
    ap.add_argument("--logcheck-heartbeat", type=Path, help="run: the file a watcher (`logcheck --heartbeat`) refreshes; no new run starts while it is old, missing or alarming")
    ap.add_argument("--logcheck-off", metavar="REASON", help="run: start without the kept-log check; the reason goes on every run record and in LOGCHECK.jsonl")
    ap.add_argument("--heartbeat", type=Path, help="logcheck: leave the answer in this file for `run`")
    ap.add_argument("--launch-config", type=Path, help="run: the campaign's launch JSON; its process_reservations['fault_calibration'] says the slot keys this process leases from "
                    "and the sandboxes it holds, and its reservation_dir (or ICSA_RESERVATION_DIR) where it takes its lock for as long as it runs")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.command == "run" and not (a.traefik_setting and a.data_path):
        raise SystemExit("run needs --traefik-setting and --data-path: every run is reported with them")
    if a.command == "run":                   # a launch cannot skip the kept-log check by leaving it out: it says which, and an off says why (the lead, 2 Nov)
        off = (a.logcheck_off or "").strip()
        if bool(a.logcheck_heartbeat) == bool(off):
            raise SystemExit("run needs exactly one of --logcheck-heartbeat FILE (a watcher refreshing `logcheck --heartbeat FILE`) and --logcheck-off REASON")
        if a.logcheck_heartbeat and (why := heartbeat_problem(a.logcheck_heartbeat)):
            raise SystemExit(f"run refused: {why}")
    if a.command == "verdict":
        import pandas as pd

        from .fidelity import IncompleteMatrix, h3_verdict
        try:
            print(json.dumps(h3_verdict(pd.read_csv(a.out / "h3_table.csv"), claim=Ledger(a.out / "LEDGER.json").claimed())))
        except IncompleteMatrix as e:
            print(f"INCOMPLETE: {e}", file=sys.stderr)
            raise SystemExit(3) from None
        return
    if a.command == "logcheck":
        got = log_check(a.out)
        print(json.dumps(got))
        if a.heartbeat:
            write_heartbeat(a.heartbeat, got)
        if got["alarms"]:
            raise SystemExit(4)
        return
    if a.command == "measure":
        if not a.image:
            raise SystemExit("measure needs --image")
        measure(a.out, a.image, a.n, layout=Layout(a.layout))
        return
    ledger = Ledger(a.out / "LEDGER.json")
    state = a.out / "plan.pkl"
    if a.command == "plan":
        if a.seed is None:
            raise SystemExit("plan needs --seed: the science agent sets it, before the claim")
        iid, req = _calibration_instance()
        mans, ids_sha = _manifests(a.ids)
        plan, claim = calibration_plan(a.seed, a.out / "LEDGER.json", required=req, manifests=mans)
        state.write_bytes(pickle.dumps({"plan": plan, "instance": iid, "required": req, "manifests": mans}))
        info = {"matrix_id": claim.matrix_id, "sha": claim.sha, "seed": a.seed, "runs": len(plan), "instance": iid,
                "ids": str(a.ids), "ids_sha256": ids_sha, "planned_utc": utc_ms(), "reruns": RERUN_RULE}
        (a.out / "PLAN.json").write_text(json.dumps(info, indent=1))
        print(json.dumps(info))
        return
    st = pickle.loads(state.read_bytes())
    claim = ledger.claimed()
    from .ledger import matrix_sha
    if matrix_sha(st["plan"]) != claim.sha:
        raise SystemExit("plan.pkl does not match the ledger's claimed matrix")
    runs_dir = a.out / "runs"
    runs_dir.mkdir(exist_ok=True)
    if a.command == "run":
        if not a.image:
            raise SystemExit("run needs --image")
        from icsa.harness import reservation as R
        from .matcher import load_slot_map
        try:         # its own slot keys and its reservation, or no run: without them it would lease from the pool the agent runs share (the campaign counts it by this lock)
            R.claim("fault_calibration", a.launch_config, {k: s.option for k, s in load_slot_map(REPO / "config" / "slot_map.json").items()},
                    options={p.scenario.option.value for p in st["plan"]}, concurrency=1 if a.seam else a.concurrency)
        except R.ReservationError as e:
            raise SystemExit(f"run refused: {e}") from None
        if not a.seam:             # science, 3 Nov: the old site_g's finished runs are run again on this head, after the replacements; their records stay, apart
            again = mark_kept_for_rerun(st["plan"], claim, ledger, runs_dir)
            if again:
                print(json.dumps({"kept_runs_put_back_for_a_rerun": len(again), "sids": again}))
        RUN_TAGS.update(traefik_setting=a.traefik_setting, data_path=a.data_path)
        import getpass
        LOGCHECK.clear()
        LOGCHECK.update({"mode": "off", "reason": off, "by": getpass.getuser()} if off else {"mode": "heartbeat", "file": str(a.logcheck_heartbeat)})
        _note_logcheck(a.out, {"event": "run_started", **LOGCHECK})

        def logcheck_gate() -> str | None:
            why = None if off else heartbeat_problem(a.logcheck_heartbeat)
            if why:
                _note_logcheck(a.out, {"event": "paused", "why": why})
            return why
        from icsa.harness.config import load_config
        from icsa.harness.real_sandbox import sandbox_config
        from icsa.sandbox.config import pin_image
        cfg = sandbox_config(a.image, pin_image(a.image), sandbox_limits=load_config().sandbox_limits)
        print(run_calibration(st["plan"], claim, ledger, st["required"], st["manifests"], cfg, runs_dir,
                              pause_file=a.pause_file, concurrency=1 if a.seam else a.concurrency,
                              only=seam_sids(st["plan"]) if a.seam else None, gate=logcheck_gate))
    elif a.command == "pull":
        from .matcher import load_slot_map
        users = [s.user for s in load_slot_map(REPO / "config" / "slot_map.json").values() if s.option in ("T", "D", "M")]
        print(json.dumps(pull_logs(a.out, users, f"{PREFIX}{claim.sha[:8]}-")))
    else:
        waiting = ledger.pending() + _started(ledger)       # a started run is a crash's: `run` will replace it
        if waiting and not a.partial:
            raise SystemExit(f"score: {len(waiting)} planned run(s) still pending or to be replaced, and replacements run before "
                             "any cell is scored. Finish them, or pass --partial for a report (the ledger records it)")
        if waiting:
            ledger.note_partial_score(len(waiting))
        from .matcher import KnowledgePlane, load_knowledge_plane, load_slot_map
        sm_path = REPO / "config" / "slot_map.json"
        kp = load_knowledge_plane(sm_path) or KnowledgePlane()
        done = {s_ for s_, v in ledger._read().get("state", {}).items() if v == "done"}
        diag: dict = {}
        runs = score(st["plan"], claim, st["required"], st["manifests"], runs_dir, (a.out / "audit.log").read_text(),
                     (a.out / "traefik.jsonl").read_text(), load_slot_map(sm_path), kp, done=done,
                     pulled_at=capture_times(a.out), gaps=capture_gaps(a.out), diag=diag)
        tags = tags_of(st["plan"], claim, runs_dir, a.out)
        write_rows(runs, claim, ledger, st["instance"], a.out, images=images_of(st["plan"], claim, runs_dir, a.out), tags=tags)
        apart_sids = ledger.rerun_sids()
        if apart_sids:             # the old site_g's runs, from their kept records, apart from the primary table (which reads the reruns only)
            from .fidelity import h3_table
            old = score(st["plan"], claim, st["required"], st["manifests"], runs_dir, (a.out / "audit.log").read_text(),
                        (a.out / "traefik.jsonl").read_text(), load_slot_map(sm_path), kp, done=done,
                        pulled_at=capture_times(a.out), gaps=capture_gaps(a.out), apart=set(apart_sids))
            t = h3_table(old, claim=claim, lost_sids=[], withheld=[x for x in claim.planned if x not in set(apart_sids)])
            t.to_csv(a.out / "h3_table_old_site_g_apart.csv", index=False)
            t.to_json(a.out / "h3_table_old_site_g_apart.json", orient="records")
            diag["old_site_g_apart_runs"] = len({r.scenario.sid for r in old})
        from .gatecheck import verdict
        gvt = diag.pop("gate_vs_traefik", [])
        (a.out / "gate_vs_traefik.json").write_text(json.dumps({"verdict": verdict(gvt), "runs": gvt}, indent=1))
        print(json.dumps({"fault_runs": len(runs), "lost": len(ledger.lost()),
                          "tagged_after_the_run": len(tagged_after_the_run(tags)), "untagged_runs": len(untagged(tags)),
                          "invalid": sum(not r.scored for r in runs), "gate_vs_traefik": verdict(gvt), **diag}))


if __name__ == "__main__":
    main()
