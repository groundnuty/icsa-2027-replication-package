"""The process that stands for `docker run -d` of a command (the sandbox's gate; the agent's exec server): it runs the container's command under `apptainer exec` and keeps what Docker's
daemon would keep.

  * waits for the container's sandbox address (a gate is started on `bridge` and the harness connects it to its sandbox network a moment later: it must bind on that address) for at
    most GATE_ADDR_WAIT_S, then starts whether or not it came;
  * `docker run -d` has already written `running` and StartedAt (once: they never change); this writes `exited` with the exit code and FinishedAt when `apptainer` returns (a death by
    signal is 128+signal, as Docker has it; the gate's SIGTERM handler exits 0, which is what `Sandbox._stop_gate_for_collection` needs to see);
  * records the container's command (its pid and start time: `State.Pid`, and what `quiesce` leaves alone as Docker leaves init alone);
  * enforces the container's memory limit (`--memory`) as the kernel's cgroup would, ten times a second: when the processes' anon+shmem is over it, the one process with the most of it
    is killed (not the container's command), `oom` and `oom_kill` are counted, and the totals, the peak and the sums are published for the synthetic cgroup (synthcg.py);
  * its stdout and stderr are the container's (docker logs).
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time

from . import pool, procs, quota
from .common import NEVER, ShimError, flock, load_container, now_iso, proc_stat, read_json, write_json
from .dockercli import GATE_ADDR_WAIT_S, apptainer_cmd, preexec_for

GUARD_PERIOD_S = 0.1


def set_state(cdir, **kw) -> None:
    with flock(cdir / "state.lock"):
        st = read_json(cdir / "state.json", {})
        st.update(kw)
        write_json(cdir / "state.json", st)


def rss_of(pid: int):
    """(anon, file, shmem) bytes of a process, None when it is gone."""
    try:
        got = {}
        for ln in open(f"/proc/{pid}/status"):
            k, _, v = ln.partition(":")
            if k in ("RssAnon", "RssFile", "RssShmem"):
                got[k] = int(v.split()[0]) * 1024
        return got.get("RssAnon", 0), got.get("RssFile", 0), got.get("RssShmem", 0)
    except (OSError, ValueError, IndexError):
        return None


def guard(cdir, spec: dict, token: str, stop: threading.Event) -> None:
    """The memory guard and the sampler of the container's memory. Never raises: a failure here is logged and the container goes on (an unguarded run is a known departure, not a crash)."""
    raw = spec.get("limits", {}).get("memory")
    limit = quota.parse_size(raw) if raw else None
    enforce = os.environ.get("HPCSBX_MEM_GUARD", "on") != "off"
    counters = {"oom": 0, "oom_kill": 0}
    peak = 0
    main = None
    while not stop.is_set():
        try:
            if main is None:
                found = procs.find_main(token)
                if found:
                    main = found[0]
                    set_state(cdir, main_pid=found[0], main_start=found[1])
            if main is None:                  # not yet known which process is the container's command: the guard must never pick it as a victim, so it samples without enforcing until it is
                stop.wait(0.02)
                continue
            ps = procs.pids(cdir)
            per = {p: r for p in ps if (r := rss_of(p)) is not None}
            anon = sum(r[0] for r in per.values())
            fil = sum(r[1] for r in per.values())
            shm = sum(r[2] for r in per.values())
            if limit and enforce and anon + shm > limit:
                # the exec server is never a victim (a cell is: that is what a memory-limit outcome of a cell is); a gate's or a sidecar's command IS the workload, and dies at its limit as it would
                victims = sorted(((r[0] + r[2], p) for p, r in per.items() if not (spec.get("execd") and p == main)), reverse=True)
                if victims:
                    # published BEFORE the kill: the cell's exit (137) must never be seen by the harness with the old counters, or a memory-limit outcome reads as an unexplained kill and is retried
                    counters = {"oom": counters["oom"] + 1, "oom_kill": counters["oom_kill"] + 1}
                    write_json(cdir / "memstat.json", {"anon": anon, "file": fil, "shmem": shm, "peak": max(peak, anon + fil + shm), **counters, "t": time.time()})
                    try:
                        os.kill(victims[0][1], signal.SIGKILL)
                    except OSError:
                        counters = {"oom": counters["oom"] - 1, "oom_kill": counters["oom_kill"] - 1}      # it had gone already: nothing was killed by this
            peak = max(peak, anon + fil + shm)
            write_json(cdir / "memstat.json", {"anon": anon, "file": fil, "shmem": shm, "peak": peak, **counters, "t": time.time()})
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"hpcsbx: memory guard: {type(e).__name__}: {e}\n")
        stop.wait(GUARD_PERIOD_S)


def find_main_only(cdir, token: str, stop: threading.Event) -> None:
    """Record the container's command (pid and start time) for `State.Pid`; nothing else (a pool step is limited by the kernel)."""
    while not stop.is_set():
        try:
            found = procs.find_main(token)
            if found:
                set_state(cdir, main_pid=found[0], main_start=found[1])
                return
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"hpcsbx: find main: {type(e).__name__}: {e}\n")
        stop.wait(0.05)


def main(argv: list) -> int:
    name = argv[0]
    c = load_container(name)
    cdir, spec = c["dir"], c["spec"]
    set_state(cdir, supervisor_pid=os.getpid(), supervisor_start=(proc_stat(os.getpid()) or (None,) * 4)[3])
    try:
        deadline = time.monotonic() + GATE_ADDR_WAIT_S
        st = read_json(cdir / "state.json", {})
        while spec.get("is_gate") and not st.get("sandbox_ip") and time.monotonic() < deadline:
            time.sleep(0.02)
            st = read_json(cdir / "state.json", {})
        argv2, penv = apptainer_cmd(spec, cdir, spec["cmd"], None, {}, st)
        kind = pool.kind_of(spec) if pool.enabled() else None
        if kind:
            # the command runs in a Slurm step of its own (memory.max by the kernel, a cpuset, real counters): claim one, or fail: never run it unlimited
            want = spec.get("limits", {}).get("memory")
            want_b = quota.parse_size(want) if want else None
            sock = None
            for attempt in range(5):             # a slot that turned out to be a newer step than the one claimed is dropped and another is claimed
                slot = pool.claim(kind, name, want_b)
                set_state(cdir, pool_slot=f"{kind}/{slot['dir'].name}", cgroup=slot["ready"].get("cgroup"), cores=slot["ready"].get("cores"), step_node=slot["ready"].get("node"),
                          step_id=slot["ready"].get("step"), memory_max=slot["ready"].get("memory_max"))
                adj = spec.get("limits", {}).get("oom-score-adj")
                try:
                    sock, pid = pool.start(slot, argv2, penv, cdir / "env.json", None, cdir / "out.log", cdir / "err.log", int(adj) if adj is not None else None)
                    break
                except BaseException as e:  # noqa: BLE001
                    pool.release(slot)
                    if not getattr(e, "stale", False) and not isinstance(e, (ConnectionError, FileNotFoundError, OSError)):
                        raise
                    time.sleep(0.5)
            if sock is None:
                raise ShimError("could not hand the command to a pool step in 5 tries")
            p = None
        else:
            p = subprocess.Popen(argv2, env=penv, stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr, preexec_fn=preexec_for(spec))
    except BaseException as e:  # noqa: BLE001 -- `docker run -d` has said "running": say what became of it, or inspect goes on saying it
        sys.stderr.write(f"hpcsbx: the container could not be started: {type(e).__name__}: {e}\n")
        set_state(cdir, status="exited", running=False, exit_code=126, finished_at=now_iso(), error=f"{type(e).__name__}: {e}"[:300])
        return 1
    token = penv["APPTAINERENV_HPCSBX_CID"]
    gone = (lambda: p.poll() is not None) if p is not None else (lambda: False)
    threading.Thread(target=procs.note_namespace, args=(cdir, token, 20.0, gone), daemon=True).start()
    stop = threading.Event()
    if p is not None:       # not in a pool step: the userspace memory guard
        threading.Thread(target=guard, args=(cdir, spec, token, stop), daemon=True).start()
    else:                   # in a pool step the kernel enforces the limit and counts; a guard would only double it
        threading.Thread(target=find_main_only, args=(cdir, token, stop), daemon=True).start()
    rc = p.wait() if p is not None else pool.wait(sock)
    stop.set()
    code = rc if rc >= 0 else 128 - rc
    set_state(cdir, status="exited", running=False, exit_code=code, finished_at=now_iso())
    return 0
