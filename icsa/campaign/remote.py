"""The remote host's side of a two-host campaign (icsa/campaign/hosts.py): the forced command the dispatcher's ssh reaches.

    python -m icsa.campaign.remote start <run_dir>          the spec on stdin; starts the run detached, once per run dir
    python -m icsa.campaign.remote wait <run_dir> [--timeout S]   exit 0 + the result, 3 still running, 4 the worker ended without one
    python -m icsa.campaign.remote kill <run_dir>           stops the run's worker (TERM, then KILL), if it runs
    python -m icsa.campaign.remote pack <run_dir>           the run dir as a tar on stdout
    python -m icsa.campaign.remote probe [--image ID]       memory, disk, live runs, code tree hash, the pinned image's presence,
                                                            and this host's own endpoints.json (its site_a supervisor's)
    python -m icsa.campaign.remote slotprobe [--no-fp M,..] one slot-equality read of the slot on stdin, made from this host
    python -m icsa.campaign.remote scripted-start <dir>     {"argv": [...]} on stdin: an allowed scripted command, detached, once per dir
    python -m icsa.campaign.remote marker <dir> <name> [--set]   a barrier marker: exit 0 if it exists (after creating it with --set)

The worker runs the same executor the campaign would run locally (`icsa.harness.run:execute_run`), in its own session, so a
dropped ssh connection does not stop it; the dispatcher reattaches with `wait`. Run dirs must lie under this host's campaign
root (ICSA_REMOTE_ROOT, default ICSA_DATA/runs/campaign), and the executor is this host's own setting (ICSA_REMOTE_EXECUTOR),
never the caller's. A run dir holds `remote_spec.json` (the claim), `remote_job.json` (the worker) and `remote_result.json`.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Any

from icsa import paths

SPEC, JOB, RESULT, LOG = "remote_spec.json", "remote_job.json", "remote_result.json", "remote_worker.log"
KILLED = "remote_killed"         # a tombstone: kill was asked for; a worker that starts after it exits at once
START_WAIT_S = 30.0              # how long a start waits for its worker to record itself
CLEAN_WAIT_S = 30.0              # how long a clean waits for a worker that wrote its result to exit
REAPER = "remote_reaper.json"    # the reaper's own pid and last try
REAP_RETRY_S = 60.0              # a sandbox that could not be shown gone is tried again this often
REAP_STILL_UP = 9                # exit code: something of the dead run's sandbox is still there
LIVE = ".remote-live"            # one marker per running worker, so a probe never scans every run dir
DEFAULT_EXECUTOR = "icsa.harness.run:execute_run"


def root() -> Path:
    return Path(os.environ.get("ICSA_REMOTE_ROOT", str(paths.RUNS / "campaign"))).resolve()


def scripted_root() -> Path:
    """Where scripted work started from the dispatcher (the two-host curve, the equivalence check) keeps its dirs."""
    return Path(os.environ.get("ICSA_REMOTE_SCRIPTED_ROOT", str(paths.DATA_ROOT / "multihost"))).resolve()


# scripted-start: the only commands the caller may start, as argv prefixes run from this tree with its own interpreter (no shell)
SCRIPTED = {"curve-part": ["-m", "icsa.scripted", "curve-part"],
            "equivalence-run": ["tools/host_equivalence.py", "run"],
            "latency": ["tools/host_equivalence.py", "latency"]}
MARKER_RE = __import__("re").compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
FILE_RE = __import__("re").compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")    # files a scripted part carries into its own directory (the duty profile)
MAX_FILES_BYTES = 8 << 20


def checked_dir(p: str, scripted: bool = False) -> Path:
    """Validate a caller's dir (pattern B): inside this host's root (the campaign's, or with `scripted` the scripted root), no symlink escape."""
    d = Path(p).resolve()
    r = scripted_root() if scripted else root()
    if d == r or r not in d.parents:
        raise SystemExit(f"refused: {p!r} is not under {r}")
    return d


def _atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _live_marker(d: Path) -> Path:
    return root() / LIVE / (hashlib.sha256(str(d).encode()).hexdigest()[:32] + ".json")


def _alive(job: dict, d: Path) -> bool:
    pid = int(job.get("pid", 0))
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    try:                                       # a reused pid is not our worker
        return str(d) in Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    except OSError:
        return True


def cmd_start(d: Path, spec_bytes: bytes) -> int:
    signal.signal(signal.SIGHUP, signal.SIG_IGN)       # a dropped connection must not cut a start between its claim and its job record
    spec = json.loads(spec_bytes)
    if spec.get("kind") == "scripted":
        argv = spec.get("argv")
        if not (isinstance(argv, list) and argv and argv[0] in SCRIPTED and all(isinstance(a, str) and "\0" not in a and len(a) < 4096 for a in argv)):
            print(f"refused scripted argv: the first word must be one of {sorted(SCRIPTED)}", file=sys.stderr)
            return 7
        files = spec.get("files") or {}
        if not (isinstance(files, dict) and all(isinstance(k, str) and FILE_RE.match(k) and isinstance(v, str) for k, v in files.items())
                and sum(len(v.encode()) for v in files.values()) <= MAX_FILES_BYTES):
            print(f"refused scripted files: names [a-z0-9][a-z0-9_.-]*, text, {MAX_FILES_BYTES} bytes in all", file=sys.stderr)
            return 7
    d.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(d / SPEC, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        t0 = time.monotonic()
        while not (d / JOB).exists() and time.monotonic() - t0 < START_WAIT_S + 5:   # a first start may still be under way: it records its
            time.sleep(0.2)                                                             # worker, or gives up and stops it, within START_WAIT_S
        if (d / JOB).exists():
            print(json.dumps({"state": "already started"}))
            return 0
        print("claimed but no worker was started", file=sys.stderr)
        return 5
    with os.fdopen(fd, "w") as fh:
        fh.write(json.dumps(spec))
        fh.flush()
        os.fsync(fh.fileno())
    log = open(d / LOG, "ab")
    p = subprocess.Popen([sys.executable, "-m", "icsa.campaign.remote", "work", str(d)], stdin=subprocess.DEVNULL, stdout=log,
                         stderr=log, start_new_session=True, close_fds=True, cwd=str(Path(__file__).resolve().parents[2]))
    log.close()
    t0 = time.monotonic()
    while not (d / JOB).exists():                      # the worker writes its own job record first thing (cmd_work), so even a start cut
        if p.poll() is not None or time.monotonic() - t0 > START_WAIT_S:   # here leaves the claim with a record, and a retry finds it
            if p.poll() is None:                       # alive but silent: stop it, so "not started" (exit 5) is true
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait()
            print(f"the worker did not record itself (exit {p.poll()})", file=sys.stderr)
            return 5
        time.sleep(0.05)
    print(json.dumps({"state": "started", "pid": p.pid}))
    return 0


def _record_job(d: Path, spec: dict) -> None:
    job = {"pid": os.getpid(), "started_epoch": time.time(), "host": spec.get("host")}
    (root() / LIVE).mkdir(parents=True, exist_ok=True)
    _atomic(_live_marker(d), json.dumps({**job, "run_dir": str(d)}))
    _atomic(d / JOB, json.dumps(job))


def _load_executor():
    mod, fn = os.environ.get("ICSA_REMOTE_EXECUTOR", DEFAULT_EXECUTOR).split(":")
    return getattr(importlib.import_module(mod), fn)


def _cfg_from(d: dict):
    from .config import BlockSpec, CampaignConfig, Price
    cfg = CampaignConfig()
    for k, v in d.items():
        if k == "blocks":
            cfg.blocks = [BlockSpec(**b) for b in v]
        elif k == "prices":
            cfg.prices = {m: Price(**p) for m, p in v.items()}
        elif hasattr(cfg, k):
            setattr(cfg, k, v)
    return cfg


def cmd_work(d: Path) -> int:
    from icsa.records import Layout, Option, RunId
    from .errors import is_infra_error

    def term(*_):
        raise SystemExit(143)
    signal.signal(signal.SIGTERM, term)
    signal.signal(signal.SIGINT, term)
    res: dict[str, Any]
    try:
        spec = json.loads((d / SPEC).read_text())
        _record_job(d, spec)
        if (d / KILLED).exists():                      # a kill came while this start was under way: never run
            return 0
        if spec.get("kind") == "scripted":            # validated at start; run from this tree, its interpreter, no shell
            argv = spec["argv"]
            for name, text in (spec.get("files") or {}).items():       # validated at start: plain names, inside this part's own directory
                _atomic(d / name, text)
            os.environ["ICSA_SLOT_KEYS"] = ",".join(spec.get("slot_keys") or [])
            rc = wait_child(subprocess.Popen([sys.executable, *SCRIPTED[argv[0]], *argv[1:]], cwd=str(Path(__file__).resolve().parents[2]),
                                             stdin=subprocess.DEVNULL))
            _atomic(d / RESULT, json.dumps({"kind": "scripted", "rc": rc}))
            return 0
        os.environ["ICSA_SLOT_KEYS"] = ",".join(spec.get("slot_keys") or [])      # this host's share only (slot_lease.allowed_keys)
        try:
            from icsa.sandbox import earlyoom
            earlyoom.name_this_driver()                                          # the host's earlyoom must never pick the driver
        except Exception:  # noqa: BLE001 - the probe reports a host whose earlyoom is not set up
            pass
        r = spec["run"]
        run = RunId(r["instance_id"], Option(r["option"]), Layout(r["layout"]), r["model"], r["seed"])
        cfg = _cfg_from(spec["cfg"])
        kw: dict[str, Any] = {"provider_cap": spec.get("provider_cap")}
        if spec.get("concurrency_at_start") is not None:
            kw["concurrency_at_start"] = spec["concurrency_at_start"]
        try:
            _load_executor()(run, int(spec["attempt"]), d, spec["slot"], cfg, **kw)
            res = {"kind": "record"}
        except Exception as e:  # noqa: BLE001 - classified as the campaign would classify it locally
            if is_infra_error(e):
                res = {"kind": "infra", "infra_kind": e.kind, "detail": e.detail}  # type: ignore[attr-defined]
            else:
                res = {"kind": "harness_error", "detail": f"{type(e).__name__}: {e}"}
        try:
            from icsa.harness import slot_lease as SL
            res["still_live"] = bool(SL._QUARANTINED)     # a teardown not proven: its sandbox may still run, so the dispatcher keeps it counted
        except Exception:  # noqa: BLE001
            res["still_live"] = True
        _atomic(d / RESULT, json.dumps(res))
        _hold_quarantines()
        return 0
    finally:
        try:
            _live_marker(d).unlink()
        except OSError:
            pass


def wait_child(child: subprocess.Popen) -> int:
    """Wait for a scripted part to end, whatever signal comes: it is in this process group and gets kill's TERM itself, then stops its own
    sandboxes (icsa.scripted's wait_for_stop); dying here, or killing it, would cut that teardown short. The handlers are no-ops, not SIG_IGN,
    so nothing is inherited by a child started later."""
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: None)
    return child.wait()


def _hold_quarantines(poll_s: float = 5.0) -> None:
    """A quarantined slot user (its sandbox could not be shown torn down) is held by THIS process's flock until the teardown is proven
    (icsa.harness.slot_lease): exiting would free it for another run while the sandbox may still use its token. So the worker stays,
    after writing its result, as long as any of its leases is in quarantine, as the campaign process would locally."""
    try:
        from icsa.harness import slot_lease as SL
    except Exception:  # noqa: BLE001
        return
    while SL._QUARANTINED:
        time.sleep(poll_s)


def cmd_wait(d: Path, timeout: float) -> int:
    t0 = time.monotonic()
    while True:
        if (d / RESULT).exists():
            print((d / RESULT).read_text())
            return 0
        try:
            job = json.loads((d / JOB).read_text())
        except (OSError, ValueError):
            job = None
        if job is None or not _alive(job, d):
            if (d / RESULT).exists():          # it finished between the two checks
                continue
            if job is not None and not _is_scripted(d):       # seen dead: its sandbox goes now, not at the next probe
                _start_reaper(d)
            print("no live worker and no result", file=sys.stderr)
            return 4
        if time.monotonic() - t0 >= timeout:
            return 3
        time.sleep(0.2)


def cmd_kill(d: Path, grace_s: float = 120.0) -> int:
    if (d / SPEC).exists():
        _atomic(d / KILLED, f"{time.time()}\n")       # first: a worker starting from here on exits at once
        t0 = time.monotonic()
        while not (d / JOB).exists() and time.monotonic() - t0 < START_WAIT_S + 5:   # a claimed start still under way: it records its worker,
            time.sleep(0.2)                                                             # or gives up and stops it (cmd_start), within START_WAIT_S
    try:
        job = json.loads((d / JOB).read_text())
    except (OSError, ValueError):
        return 0
    if not _alive(job, d):
        return 0
    pid = int(job["pid"])
    for sig, wait_s in ((signal.SIGTERM, grace_s), (signal.SIGKILL, 10.0)):
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            return 0
        t0 = time.monotonic()
        while time.monotonic() - t0 < wait_s:
            if not _alive(job, d):
                return 0
            time.sleep(0.2)
    print(f"worker {pid} survived TERM and KILL", file=sys.stderr)
    return 6


def _is_scripted(d: Path) -> bool:
    try:
        return json.loads((d / SPEC).read_text()).get("kind") == "scripted"
    except (OSError, ValueError):
        return False


def _start_reaper(d: Path) -> None:
    """A dead worker's run gets one detached reaper at a time, tried again every REAP_RETRY_S: the probe stays quick, and nothing waits for a new start."""
    try:
        j = json.loads((d / REAPER).read_text())
        if time.time() - float(j.get("at", 0.0)) < REAP_RETRY_S or _alive(j, d):
            return
    except (OSError, ValueError):
        pass
    p = subprocess.Popen([sys.executable, "-m", "icsa.campaign.remote", "reap", str(d)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True, cwd=str(Path(__file__).resolve().parents[2]))
    _atomic(d / REAPER, json.dumps({"pid": p.pid, "at": time.time()}))


def _reap_hook():
    spec = os.environ.get("ICSA_REMOTE_REAP")
    if not spec:
        return None
    mod, fn = spec.split(":")
    return getattr(importlib.import_module(mod), fn)


def cmd_reap(d: Path) -> int:
    """A worker died (SIGKILL, an OOM) and left its sandbox: icsa.sandbox.reap removes it now, logging in the run dir first. Anything still there exits
    REAP_STILL_UP and leaves the live marker, so the dispatcher keeps counting the run."""
    hook = _reap_hook()
    if hook is not None:                   # this host's own setting, never the caller's (tests: stand-in hosts have no docker)
        rc = int(hook(d))
    else:
        from icsa.sandbox import reap
        key = d.parent.name
        rc = 0 if reap.reap_run(key.split("__", 1)[1] if "__" in key else key, log_dir=d) else REAP_STILL_UP
    if rc == 0:
        try:
            _live_marker(d).unlink()
        except OSError:
            pass
    return rc


def _tree_facts(d: Path) -> tuple[int, int]:
    """(files, bytes) of what `cmd_pack` sends."""
    n = b = 0
    for p in d.rglob("*"):
        if p.is_file() and not p.is_symlink() and not p.name.endswith(".tmp"):
            n, b = n + 1, b + p.stat().st_size
    return n, b


def cmd_clean(d: Path, files: int | None = None, nbytes: int | None = None) -> int:
    """Remove a finished run's dir once the dispatcher has its copy: only with its result written and its teardown not in doubt. A worker that wrote its
    result is usually just exiting, so it gets CLEAN_WAIT_S to go; one holding a quarantined slot user says so in its result (`still_live`), and its dir
    stays whether or not the worker lives: a killed worker proves nothing about its sandbox."""
    try:
        res = json.loads((d / RESULT).read_text())
    except (OSError, ValueError):
        res = None
    if res is None and (not (d / JOB).exists() or _live_marker(d).exists()):       # no result is final only for a worker that died and was reaped
        print("refused: the run has no result yet", file=sys.stderr)
        return 8
    if res is not None and res.get("still_live"):
        print("refused: its teardown was not proven", file=sys.stderr)
        return 8
    try:
        job = json.loads((d / JOB).read_text())
    except (OSError, ValueError):
        job = None
    t0 = time.monotonic()
    while job is not None and _alive(job, d):
        if time.monotonic() - t0 >= CLEAN_WAIT_S:
            print("refused: its worker is still alive", file=sys.stderr)
            return 8
        time.sleep(0.1)
    here = _tree_facts(d)
    if (files, nbytes) != here:            # no run output goes without its copy checked by file count and bytes (lane-common, 2 Nov)
        print(f"refused: {here} here, {(files, nbytes)} landed", file=sys.stderr)
        return 8
    shutil.rmtree(d, ignore_errors=True)
    return 0


def cmd_pack(d: Path) -> int:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for p in sorted(d.rglob("*")):
            if p.is_symlink() or p.name.endswith(".tmp"):
                continue
            tf.add(p, arcname=str(p.relative_to(d)), recursive=False)
    sys.stdout.buffer.write(buf.getvalue())
    sys.stdout.buffer.flush()
    return 0


def _mem_available() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except OSError:
        pass
    return None


def cmd_probe(image: str | None) -> int:
    from icsa import codestamp
    free = []
    for p in (root(), Path(os.environ.get("ICSA_DOCKER_ROOT", "/var/lib/docker"))):
        try:
            free.append(shutil.disk_usage(p).free / 1024 ** 3)
        except OSError:
            pass
    live, unreaped = [], []
    for m in sorted((root() / LIVE).glob("*.json")) if (root() / LIVE).exists() else []:
        try:
            j = json.loads(m.read_text())
        except (OSError, ValueError):
            continue
        rd = Path(j["run_dir"])
        if _alive(j, rd):
            live.append(j["run_dir"])
        elif _is_scripted(rd):             # a scripted part keeps its own account of what it left (icsa.scripted.multihost)
            continue
        else:                              # the worker died without its `finally`: its sandbox may still run. Live until a reaper shows it gone (lane-dress, 2 Nov)
            live.append(j["run_dir"])
            unreaped.append(j["run_dir"])
            _start_reaper(rd)
    image_ok = None
    if image:
        try:
            from icsa.sandbox import hostops
            image_ok = hostops.image_id(image) == image
        except Exception:  # noqa: BLE001 - not there, or docker unreachable: either way not ok
            image_ok = False
    from .endpoints import read_endpoints
    pool = None
    try:                                   # this host's slot-user pool: waits and quarantines are invisible to the dispatcher otherwise
        from icsa.harness import slot_lease as SL
        ld = Path(os.environ.get("ICSA_LEASE_DIR", str(SL.LEASE_DIR)))
        pool = SL.pool_status(ld, SL.SLOT_MAP) if ld.is_dir() else {}
    except Exception as e:  # noqa: BLE001 - reported as unreadable, never as fine
        pool = {"_error": f"{type(e).__name__}: {e}"[:200]}
    d_use = {}
    try:                                   # what each live run's sandbox holds now: the dispatcher reserves a D run's peak less this
        from icsa.campaign.diskuse import sandbox_use
        from icsa.sandbox import reap
        wr = reap.work_root()
        for rd in live:
            k = Path(rd).parent.name
            u = sandbox_use(wr, k)
            if u is not None:
                d_use[k] = u
    except Exception:  # noqa: BLE001 - not measured: the dispatcher then reserves the whole peak
        d_use = {}
    out = {"pool": pool, "d_use": d_use, "unreaped": unreaped, "mem_available": _mem_available(), "disk_free_gib": round(min(free), 2) if len(free) == 2 else None, "live": live,
           "tree": codestamp.tree_hash(Path(__file__).resolve().parents[2]), "image_ok": image_ok,
           "endpoints": read_endpoints(os.environ.get("ICSA_ENDPOINTS_FILE", "~/icsa-paths/endpoints.json"))}
    print(json.dumps(out))
    return 0


CALLER_COMMANDS = ("start", "wait", "kill", "pack", "probe", "slotprobe", "scripted-start", "marker", "clean")      # what the dispatcher may ask for; `work` is the worker's own


def from_ssh() -> list[str]:
    """The forced command's arguments: SSH_ORIGINAL_COMMAND, split by shlex (never by a shell), first word one of CALLER_COMMANDS."""
    import shlex
    words = shlex.split(os.environ.get("SSH_ORIGINAL_COMMAND", ""))
    if not words or words[0] not in CALLER_COMMANDS:
        raise SystemExit(f"refused: {words[:1]!r} is not one of {CALLER_COMMANDS}")
    return words


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--from-ssh"]:
        argv = from_ssh()
    ap = argparse.ArgumentParser(prog="icsa.campaign.remote")
    ap.add_argument("cmd", choices=["start", "work", "reap", "wait", "kill", "pack", "probe", "slotprobe", "scripted-start", "marker", "clean"])
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--image")
    ap.add_argument("--no-fp", default="")
    ap.add_argument("--files", type=int, default=None, help="clean: the files that landed at the dispatcher")
    ap.add_argument("--bytes", type=int, default=None, help="clean: their bytes")
    ap.add_argument("--set", action="store_true")
    ap.add_argument("--scripted", action="store_true", help="wait/kill/pack: the dir is under the scripted root")
    a = ap.parse_args(argv)
    if a.cmd == "probe":
        return cmd_probe(a.image)
    if a.cmd == "slotprobe":
        from dataclasses import asdict
        from .slot_equality import http_probe
        entry = json.loads(sys.stdin.buffer.read())
        print(json.dumps(asdict(http_probe(entry, no_fp_models=frozenset(x for x in a.no_fp.split(",") if x)))))
        return 0
    if not a.run_dir:
        ap.error("run_dir is required")
    if a.cmd == "marker":
        d = checked_dir(a.run_dir, scripted=True)
        if not a.name or not MARKER_RE.match(a.name):
            raise SystemExit(f"refused marker name {a.name!r}")
        if a.set:
            d.mkdir(parents=True, exist_ok=True)
            _atomic(d / f"marker-{a.name}", f"{time.time()}\n")
        return 0 if (d / f"marker-{a.name}").exists() else 1
    if a.cmd == "scripted-start":
        return cmd_start(checked_dir(a.run_dir, scripted=True), sys.stdin.buffer.read())
    if a.cmd == "work":
        try:
            d = checked_dir(a.run_dir)
        except SystemExit:
            d = checked_dir(a.run_dir, scripted=True)
        return cmd_work(d)
    if a.cmd == "reap":                    # not in CALLER_COMMANDS: the probe starts it, for its own marker
        return cmd_reap(checked_dir(a.run_dir))
    d = checked_dir(a.run_dir, scripted=a.scripted)
    if a.cmd == "clean":
        return cmd_clean(d, a.files, a.bytes)
    if a.cmd == "start":
        return cmd_start(d, sys.stdin.buffer.read())
    if a.cmd == "wait":
        return cmd_wait(d, min(max(a.timeout, 0.0), 300.0))
    if a.cmd == "kill":
        return cmd_kill(d, grace_s=900.0 if a.scripted else 120.0)    # a scripted part's own teardown (wait_for_stop) may take minutes
    return cmd_pack(d)


def stub_execute(*a, **kw):
    """Tests: the stub executor (ICSA_STUB_PLAN) as a remote host's executor."""
    from .stub import make_stub_executor
    conc = kw.pop("concurrency_at_start", None)
    Path(a[2]).mkdir(parents=True, exist_ok=True)
    (Path(a[2]) / "stub_concurrency_at_start").write_text(f"{conc}\n")
    return make_stub_executor()(*a, **kw)


if __name__ == "__main__":
    sys.exit(main())
