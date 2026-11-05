"""A cgroup for each container that does not have one.

The harness reads each container's cgroup (`memory.events`, `memory.peak`, `memory.stat`, `cgroup.procs`) to say whether a process was OOM-killed, and a `None` where it cannot read is
a problem it retries the run for (infradeath.problems: "the cgroup's oom_kill counter could not be read"). A user on site_a cannot make a cgroup (the step's is root's, mkdir is
refused), so no run would ever count. This builds what the harness reads, from what can be known, and says where it is not the kernel's:

  * `cgroup.procs`: the container's processes (procs.py: by pid namespace);
  * `memory.stat`: anon, file and shmem are the sums, sampled ten times a second by the container's supervisor, of RssAnon, RssFile and RssShmem of those processes (RssAnon, RssFile, RssShmem of /proc/<pid>/status), NOT a cgroup's own accounting: /tmp and /dev/shm
    here are fuse2fs images on the node's tmpfs, and their data is the node's, not counted;
  * `memory.peak`: the highest sum of those three seen at a refresh (the harness refreshes once a second while a run is live), NOT the kernel's high-water mark;
  * `memory.max`: the limit the harness asked Docker for (`--memory`), which the container's supervisor enforces (the kernel sets none on this host);
  * `memory.events`: `oom` and `oom_kill` are 0 only while Slurm's own cgroup of the step (and every cgroup above it up to the job) has seen no OOM kill since the container was made.
    If one has, the file is not written: whether a process of this container was the victim is not known, and the harness retries the run, which is what not-known costs.
  * `cpu.stat` is not written: CPU seconds of the processes that have ended cannot be summed, and a partial number is worse than none (`cpu_s` is recorded as unknown).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from . import procs, quota
from .common import STATE, container_names, container_dir, flock, read_json, write_json

CGROOT = Path("/sys/fs/cgroup")


def own_cgroup_chain() -> list:
    """This process's cgroup directory and its ancestors up to (and including) the job's, which is where Slurm's memory limit sits."""
    try:
        rel = [ln.split(":", 2)[2] for ln in Path("/proc/self/cgroup").read_text().splitlines() if ln.startswith("ipv6-2")][0].strip("/")
    except (OSError, IndexError):
        return []
    parts, chain = rel.split("/"), []
    for i in range(len(parts), 0, -1):
        chain.append(CGROOT.joinpath(*parts[:i]))
        if parts[i - 1].startswith("job_"):
            break
    return chain


def step_oom_kills() -> "int | None":
    """Sum of `oom_kill` over the step's cgroup chain, or None when any of them cannot be read."""
    chain = own_cgroup_chain()
    if not chain:
        return None
    total = 0
    for d in chain:
        try:
            for ln in (d / "memory.events").read_text().splitlines():
                k, _, v = ln.partition(" ")
                if k == "oom_kill":
                    total += int(v)
        except (OSError, ValueError):
            return None
    return total


def _rss_sums(pids: list) -> dict:
    out = {"anon": 0, "file": 0, "shmem": 0}
    for p in pids:
        try:
            for ln in Path(f"/proc/{p}/status").read_text().splitlines():
                k, _, v = ln.partition(":")
                if k in ("RssAnon", "RssFile", "RssShmem"):
                    out[{"RssAnon": "anon", "RssFile": "file", "RssShmem": "shmem"}[k]] += int(v.split()[0]) * 1024
        except (OSError, ValueError, IndexError):
            pass                       # gone between the listing and the read
    return out


def cg_dir(cid: str) -> Path:
    return STATE / "cg" / cid


def refresh(name: str) -> "Path | None":
    """Rewrite the container's cgroup files from now and return the directory; None when there is no such container."""
    cdir = container_dir(name)
    spec = read_json(cdir / "spec.json")
    if spec is None:
        return None
    d = cg_dir(spec["id"])
    d.mkdir(parents=True, exist_ok=True)
    with flock(d / "refresh.lock"):          # the harness's sampler thread and its main thread both refresh: one at a time, or a kill counted by one is overwritten by the other's older read
        return _refresh_locked(cdir, spec, d)


def _real_files(cdir: Path, d: Path, pids: list) -> bool:
    """A container in a pool step (hpcsbx/pool.py): the kernel's own memory.events, memory.peak, memory.stat, memory.max and cpu.stat of the step's cgroup, COPIED (each refresh) into the directory the
    harness reads; only `cgroup.procs` is built (the step's processes are in sub-cgroups, and the container's are found by pid namespace). Copies, not links: when the step ends Slurm removes its cgroup,
    and the last copy is what a later read (the gate's state after its stop) still sees, as the final value, instead of a dangling link that fails the read. False when this container has no step."""
    cg = (read_json(cdir / "state.json", {}) or {}).get("cgroup")
    if not cg:
        return False
    live = Path(cg, "memory.events").exists()
    if not live and not (d / "memory.events").exists():
        return False
    if live:
        for fn in ("memory.events", "memory.peak", "memory.stat", "memory.max", "cpu.stat"):
            try:
                text = (Path(cg) / fn).read_text()
            except OSError:
                continue                            # the step ended between the two reads: keep the last copy
            tmp = d / f".{fn}.{os.getpid()}.tmp"
            tmp.write_text(text)
            os.replace(tmp, d / fn)
    (d / "cgroup.procs").write_text("".join(f"{p}\n" for p in pids))
    return True


def _refresh_locked(cdir: Path, spec: dict, d: Path) -> Path:
    """The files from the supervisor's record (supervisor.guard samples the container's memory ten times a second, enforces `--memory` and counts the kills), and from the processes now."""
    pids = procs.pids(cdir)
    if _real_files(cdir, d, pids):
        return d
    ms = read_json(cdir / "memstat.json")
    if ms and time.time() - ms.get("t", 0) < 5:
        sums, peak = {"anon": ms["anon"], "file": ms["file"], "shmem": ms["shmem"]}, ms["peak"]
    else:                                  # no supervisor sampling (it has exited, or this container has none): the processes now, and the highest seen at a refresh
        sums = _rss_sums(pids)
        peak = max(read_json(d / "peak.json", {"peak": 0})["peak"], sums["anon"] + sums["file"] + sums["shmem"], (ms or {}).get("peak", 0))
        write_json(d / "peak.json", {"peak": peak})
    counters = {"oom": (ms or {}).get("oom", 0), "oom_kill": (ms or {}).get("oom_kill", 0)}      # kept for good: a kill counted once stays counted
    (d / "cgroup.procs").write_text("".join(f"{p}\n" for p in pids))
    (d / "memory.stat").write_text("".join(f"{k} {v}\n" for k, v in sums.items()))
    (d / "memory.peak").write_text(f"{peak}\n")
    raw = spec.get("limits", {}).get("memory")
    (d / "memory.max").write_text(f"{quota.parse_size(raw)}\n" if raw else "max\n")      # the limit the supervisor enforces, which is what the cgroup's would say
    base = read_json(cdir / "state.json", {}).get("oom_baseline")
    now = step_oom_kills()
    ev = d / "memory.events"
    if base is not None and now is not None and now == base:
        ev.write_text(f"low 0\nhigh 0\nmax 0\noom {counters['oom']}\noom_kill {counters['oom_kill']}\noom_group_kill 0\n")
    elif ev.exists():
        ev.unlink()                    # not known: see the module docstring
    return d


def by_id(cid: str) -> "str | None":
    for n in container_names():
        s = read_json(container_dir(n) / "spec.json", {})
        if s and s.get("id") == cid:
            return n
    return None
