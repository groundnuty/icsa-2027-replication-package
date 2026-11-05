"""Host sampler, dispatch gate and stepped ramp for sandbox work on this host (science's order on #2, 2 Nov 00:33Z).

The VM froze on 1 Nov at 23:48Z with 16 calibration sandboxes in flight (12 of them M, each with a oneclient FUSE mount).
The order: ramp in steps (4, 8, 12, 16) with host samples every 5 s (MemAvailable, load, D-state tasks, mount count), and
stop dispatching at the first D-state build-up.

`HostSampler` reads, every `period_s` (5 s): MemAvailable, the load averages, the tasks (threads, /proc/*/task/*/stat) and
the processes (/proc/*/stat) in D state, each D task's command name, wait channel and whether it runs in a container,
the total mount count and the FUSE mount count (/proc/self/mountinfo). It appends one JSON line per sample (flushed and
fsynced: the last samples before a freeze are the evidence) to a path the caller gives. The mount table is read off the
sampling thread with a deadline: the hypothesised failure blocks mount-namespace operations, and reading mountinfo
waits on the same lock, so a read that hangs is itself a finding (`mountinfo_hung`), never a hung sampler. Each sample
also carries what the M teardowns reported since the sampler started, from any process (`teardown_events`: readers stuck
in D, FUSE aborts, sandboxes held; `teardown_counts`: the running totals; see teardown.py).

`DispatchGate.allow_more()` is False:
  * LATCHED, until `reset()` by a person, only for what a person must look at: a stuck FUSE path. That is user-space tasks in a FUSE wait channel
    (`request_wait_answer`, `fuse_*`), each in D for `persist_samples` (3) consecutive samples, i.e. stuck for 10 s or more at the 5 s period:
    `container_d_max` (8) or more inside containers, or `host_d_max` (2) or more outside any (dockerd, runc, a mount helper: the stronger sign). A
    transient D (a page-cache read through FUSE waits killably and shows as D) is not a build-up; a stuck one is;
  * LATCHED at a much higher bar for every other wait channel, an unreadable one included: `other_d_max` (8) or more user-space tasks in D for
    `other_persist_samples` (6, so 25 s or more). Disk-heavy work anywhere on a shared host sits in jbd2_log_wait_commit and
    folio_wait_bit_common: two such tasks for three samples would have latched during the validation on the VM (2 Nov), with no sandbox involved.
    Kernel threads are recorded but never counted (jbd2 sits in D whenever the disk is busy). Each task's process name, command line and cgroup are in
    the sample either way, because the first log of that latch could not say whose they were. Also latched when the mount table cannot be read
    within the deadline, and when a teardown held a sandbox or a FUSE abort failed: a mount nothing could release. A
    successful abort is recorded and does not close the gate: readers killed mid-read at a time cap can need one;
  * while MemAvailable is below `mem_min_gib` (8 GiB); it opens again when memory recovers;
  * while the newest sample is older than 3 periods, or could not read the D states or the memory (unknown is not a pass).
The thresholds are PROVISIONAL: the validation run (one M sandbox at a time, on the lead's GO) gives the baseline.

`StepRamp` takes the levels (4, 8, 12, 16): a level is held until `min_completed` runs DISPATCHED AT THAT LEVEL have
completed, then the ramp steps up if the gate is open. It never steps again once the gate has closed for something the
host showed (not knowing, such as a stale sample, only holds it), and it admits nothing while the gate is closed.

How a dispatcher uses it (calibration runner, scripted curve, K runs; not wired yet):

    with HostSampler(out_dir / "host_samples.jsonl") as sampler:
        gate = DispatchGate(sampler)
        ramp = StepRamp(gate, levels=(4, 8, 12, 16), min_completed=4)
        for job in jobs:
            while not ramp.may_dispatch(len(running)):
                if gate.latched: stop dispatching (record gate.reason); break out
                wait for a running job to finish, with a timeout of a few seconds (with the gate closed nothing may
                be running, so an untimed wait never returns)
            ticket = ramp.dispatched()
            start job; when it ends: ramp.completed(ticket)
"""
from __future__ import annotations

import collections
import dataclasses
import datetime as dt
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Callable

from icsa.paths import DATA_ROOT

from . import hostops as H
from .teardown import EVENTS_FILE, TEARDOWN_LOG_DIR

PROC = Path("/proc")
GIB = 1024 ** 3
DEFAULT_TEARDOWN_EVENTS = DATA_ROOT / "sandboxes" / TEARDOWN_LOG_DIR / EVENTS_FILE   # SandboxConfig's default work root


# ------------------------------------------------------------------------------------------------ reading /proc
PF_KTHREAD = 0x00200000


def _state_of(stat_text: str) -> tuple[str, str, bool] | None:
    """(state, comm, kernel thread?) from a /proc stat line; the command name may hold spaces and parentheses, so the
    fields are counted from the LAST ')'. The kernel-thread flag is PF_KTHREAD in field 9 (flags)."""
    i = stat_text.rfind(")")
    if i < 0:
        return None
    rest = stat_text[i + 2:].split()
    if not rest:
        return None
    kthread = len(rest) > 6 and rest[6].isdigit() and bool(int(rest[6]) & PF_KTHREAD)
    return rest[0], stat_text[stat_text.find("(") + 1:i], kthread


def _in_container(cgroup_text: str | None) -> bool | None:
    if cgroup_text is None:
        return None
    return any(k in cgroup_text for k in ("docker-", "/docker/", "containerd", "libpod-"))


def _read(p: Path) -> str | None:
    try:
        return p.read_text()
    except (OSError, UnicodeDecodeError):
        return None


def read_meminfo_available(proc: Path = PROC) -> int | None:
    text = _read(proc / "meminfo")
    for line in (text or "").splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            return int(parts[1]) * 1024 if len(parts) >= 2 and parts[1].isdigit() else None
    return None


def read_loadavg(proc: Path = PROC) -> tuple[float, float, float] | None:
    text = _read(proc / "loadavg")
    try:
        a, b, c = text.split()[:3]
        return float(a), float(b), float(c)
    except (AttributeError, ValueError):
        return None


def _sudo_wchans(paths: list[Path], timeout_s: float = 3.0) -> dict[str, str]:
    """{path: wait channel} through one bounded sudo. `grep -H` names each file, and goes on past a task that has gone."""
    if not paths:
        return {}
    r = H.sudo_bounded("grep", "-H", "", *[str(p) for p in paths], timeout_s=timeout_s)
    out = {}
    for line in r.stdout.splitlines():
        path, _, val = line.rpartition(":")
        if path:
            out[path] = val.strip()
    return out


def read_d_state(proc: Path = PROC, detail_max: int = 64, wchan_sudo_max: int = 4096, list_max: int = 4096) -> dict | None:
    """The tasks (threads) and processes in D state. None when /proc cannot be listed (unknown, never zero).
    `tasks`: [{tid, pid, comm, kthread, wchan, in_container}] for every D task up to `list_max`, far above anything but a host in
    trouble, because the gate judges persistence on this list and a cap near normal levels could hide the build-up; `unlisted` counts
    the rest, which itself closes the gate. Every user-space task gets its wait channel, command line and cgroup, since the gate decides on
    them; kernel threads, which never count, only the first `detail_max` (`truncated` says some had none read). Without ptrace access the kernel
    answers "0" for a wait channel (measured on dockerd here: "0" without sudo, "futex_wait_queue" with): that is None (unknown), and such tasks
    are read through one bounded sudo, user-space ones first, at most `wchan_sudo_max`."""
    try:
        pids = [e.name for e in os.scandir(proc) if e.name.isdigit()]
    except OSError:
        return None
    d_procs, tasks, n_tasks = 0, [], 0
    cgroups: dict[str, str | None] = {}
    for pid in pids:
        pst = _state_of(_read(proc / pid / "stat") or "")
        if pst is None:
            continue                     # gone meanwhile
        if pst[0] == "D":
            d_procs += 1
        try:
            tids = [e.name for e in os.scandir(proc / pid / "task") if e.name.isdigit()]
            entries = [(tid, _state_of(_read(proc / pid / "task" / tid / "stat") or "")) for tid in tids]
        except OSError:
            entries = [(pid, pst)]       # the task list is unreadable: the main thread's state stands for the process
        for tid, tst in entries:
            if tst is None or tst[0] != "D":
                continue
            n_tasks += 1
            if n_tasks > list_max:
                continue
            detailed = not tst[2] or n_tasks <= detail_max       # only user-space tasks count, so a cap on them could hide a stuck one
            wchan = (_read(proc / pid / "task" / tid / "wchan") or "").strip() if detailed else ""
            if pid not in cgroups:                # one read per process, however many of its threads are in D
                cgroups[pid] = _read(proc / pid / "cgroup")
            task = {"tid": int(tid), "pid": int(pid), "comm": tst[1], "kthread": tst[2],
                    "wchan": wchan if wchan and wchan != "0" else None, "in_container": _in_container(cgroups[pid])}
            if detailed:                          # whose it is: "python" alone cannot say which job on a shared host
                task["cmd"] = (_read(proc / pid / "cmdline") or "").replace("\0", " ").strip()[:160] or None
                task["cgroup"] = ((cgroups[pid] or "").strip().rsplit("/", 1)[-1][:100]) or None
            tasks.append(task)
    unknown = sorted((t for t in tasks if "cmd" in t and t["wchan"] is None), key=lambda t: bool(t["kthread"]))[:wchan_sudo_max]
    if unknown:
        got = _sudo_wchans([proc / str(t["pid"]) / "task" / str(t["tid"]) / "wchan" for t in unknown])
        for t in unknown:
            v = got.get(str(proc / str(t["pid"]) / "task" / str(t["tid"]) / "wchan"))
            t["wchan"] = v if v and v != "0" else None
    return {"d_tasks": n_tasks, "d_procs": d_procs, "tasks": tasks, "truncated": n_tasks > detail_max, "unlisted": n_tasks - len(tasks)}


def read_mounts(proc: Path = PROC, timeout_s: float = 5.0) -> dict:
    """{"mounts", "fuse_mounts", "mountinfo_hung"}: counts from the host's mountinfo, read with a deadline."""
    text = H.read_text_bounded(proc / "self" / "mountinfo", timeout_s)
    if text is None:
        return {"mounts": None, "fuse_mounts": None, "mountinfo_hung": True}
    return {"mounts": sum(1 for x in text.splitlines() if x.strip()), "fuse_mounts": len(H.fuse_mounts(text)),
            "mountinfo_hung": False}


def take_sample(proc: Path = PROC, mountinfo_timeout_s: float = 5.0) -> dict:
    t0 = time.monotonic()
    load = read_loadavg(proc)
    d = read_d_state(proc)
    s = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"), "mono": round(time.monotonic(), 3),
         "mem_available_bytes": read_meminfo_available(proc),
         "load1": load[0] if load else None, "load5": load[1] if load else None, "load15": load[2] if load else None,
         "d_tasks": d["d_tasks"] if d else None, "d_procs": d["d_procs"] if d else None,
         "d_list": d["tasks"] if d else None, "d_truncated": d["truncated"] if d else None, "d_unlisted": d["unlisted"] if d else None,
         **read_mounts(proc, mountinfo_timeout_s)}
    s["sample_s"] = round(time.monotonic() - t0, 3)
    return s


# ------------------------------------------------------------------------------------------------ the sampler
class HostSampler:
    """Samples the host every `period_s` in a daemon thread and appends each sample to `path` (JSONL). Listeners
    (`on_sample`) see each sample after it is written. Used as a context manager, or start()/stop()."""

    def __init__(self, path: Path | str, period_s: float = 5.0, *, proc: Path = PROC, history: int = 32,
                 sample_fn: Callable[[], dict] | None = None, mountinfo_timeout_s: float = 5.0,
                 teardown_events: Path | str | None = DEFAULT_TEARDOWN_EVENTS):
        self.path, self.period_s = Path(path), float(period_s)
        self.teardown_events = None if teardown_events is None else Path(teardown_events)
        self._td_offset = 0
        self.teardown_counts: dict[str, int] = {}
        self._sample_fn = sample_fn or (lambda: take_sample(proc, mountinfo_timeout_s))
        self.history: collections.deque = collections.deque(maxlen=history)
        self._lock = threading.Lock()
        self._listeners: list[Callable[[dict], None]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._fh = None

    def on_sample(self, fn: Callable[[dict], None]) -> None:
        self._listeners.append(fn)

    def latest(self) -> dict | None:
        with self._lock:
            return self.history[-1] if self.history else None

    def recent(self, n: int) -> list[dict]:
        with self._lock:
            return list(self.history)[-n:]

    def write(self, rec: dict) -> None:
        """Append a record (a sample, or an event such as the gate closing) to the JSONL file."""
        with self._lock:
            if self._fh is None:
                return
            try:
                self._fh.write(json.dumps(rec, default=str) + "\n")
                self._fh.flush()
                os.fsync(self._fh.fileno())
            except OSError:
                pass

    def _drain_teardown_events(self, s: dict) -> None:
        """Add to the sample the complete lines appended to the teardown events file since the last sample."""
        s["teardown_events"] = []
        if self.teardown_events is not None:
            try:
                with open(self.teardown_events, "rb") as f:
                    f.seek(self._td_offset)
                    data = f.read()
            except FileNotFoundError:
                data = b""
            except OSError as e:
                data, s["teardown_events_error"] = b"", repr(e)[:200]      # unknown, recorded; never "no events"
            end = data.rfind(b"\n") + 1                                    # a line still being written waits for the next sample
            self._td_offset += end
            for line in data[:end].splitlines():
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                s["teardown_events"].append(ev)
                kind = ev.get("step", "unknown")
                if kind == "abort" and not ev.get("ok"):
                    kind = "abort_failed"
                self.teardown_counts[kind] = self.teardown_counts.get(kind, 0) + 1
        s["teardown_counts"] = dict(self.teardown_counts)

    def sample_once(self) -> dict:
        try:
            s = self._sample_fn()
        except Exception as e:  # noqa: BLE001 -- a failed sample is recorded as unknown, never skipped
            s = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"), "mono": round(time.monotonic(), 3),
                 "mem_available_bytes": None, "d_tasks": None, "d_list": None, "error": repr(e)[:300]}
        self._drain_teardown_events(s)
        with self._lock:
            self.history.append(s)
        self.write({"kind": "sample", **s})
        for fn in list(self._listeners):
            try:
                fn(s)
            except Exception:  # noqa: BLE001
                pass
        return s

    def start(self) -> "HostSampler":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a")
        self._stop.clear()
        if self.teardown_events is not None:       # what happened before this sampler started is not its to report
            try:
                self._td_offset = self.teardown_events.stat().st_size
            except OSError:
                self._td_offset = 0
        self.sample_once()               # before start() returns: a gate asked right away has a sample to judge

        def loop():
            while not self._stop.wait(self.period_s):
                self.sample_once()
        self._thread = threading.Thread(target=loop, daemon=True, name="host-sampler")
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.period_s + 10)
        with self._lock:
            if self._fh is not None:
                self._fh.close()
                self._fh = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *a):
        self.stop()


# ------------------------------------------------------------------------------------------------ the gate
@dataclasses.dataclass(frozen=True)
class GateRule:
    mem_min_gib: float = 8.0          # below: no new dispatch until it recovers
    persist_samples: int = 3          # a task in a FUSE wait channel counts once it is in D in this many consecutive samples
    container_d_max: int = 8          # such tasks inside containers that close the gate (latched)
    host_d_max: int = 2               # such tasks outside any container that close the gate (latched)
    other_persist_samples: int = 6    # a task in any other wait channel counts only after this many
    other_d_max: int = 8              # such tasks, anywhere, that close the gate (latched)
    stale_periods: float = 3.0        # the newest sample older than this many periods: closed


FUSE_WAIT = re.compile(r"fuse|request_wait_answer")


def is_fuse_wait(task: dict) -> bool:
    return bool(task.get("wchan")) and FUSE_WAIT.search(task["wchan"]) is not None


def stuck_on_fuse(samples: list[dict], persist: int) -> list[dict]:
    """The user-space tasks in D through the whole window, seen in a FUSE wait and in no other: a task that only just reached FUSE has not been stuck
    on it. A sample whose wait channel for the task could not be read does not break the run, since not knowing is not a pass; a task never
    seen on FUSE is for the other bar. Empty when the window is short or a sample of it could not read the D states."""
    window = samples[-persist:]
    pd = persistent_d(samples, persist)
    if not pd:
        return []
    by_task = [{(t["tid"], t["comm"]): t for t in s["d_list"]} for s in window]
    out = []
    for t in pd:
        seen = [b[(t["tid"], t["comm"])] for b in by_task]
        if not t.get("kthread") and any(is_fuse_wait(x) for x in seen) and all(is_fuse_wait(x) or x.get("wchan") is None for x in seen):
            out.append(t)
    return out


def persistent_d(samples: list[dict], persist: int) -> list[dict] | None:
    """The D tasks of the newest sample that were in D (same tid and command) in each of the `persist` newest samples.
    None when one of those samples could not read the D states. Fewer samples than `persist`: none yet."""
    if len(samples) < persist:
        return []
    window = samples[-persist:]
    if any(s.get("d_list") is None for s in window):
        return None
    keysets = [{(t["tid"], t["comm"]) for t in s["d_list"]} for s in window[:-1]]
    return [t for t in window[-1]["d_list"] if all((t["tid"], t["comm"]) in ks for ks in keysets)]


def evaluate(samples: list[dict], rule: GateRule, now_mono: float, period_s: float, td_base: dict | None = None) -> dict:
    """The gate's decision on the sample history: {"allow", "latch", "host", "reason"}. `host`: closed because of what the
    host showed (a build-up, the memory floor), as against not knowing (no sample yet, stale, unreadable). Pure, so the
    thresholds can be tested."""
    if not samples:
        return {"allow": False, "latch": False, "host": False, "reason": "no sample yet"}
    s = samples[-1]
    if now_mono - float(s.get("mono", 0)) > rule.stale_periods * period_s:
        return {"allow": False, "latch": False, "host": False, "reason": f"newest sample older than {rule.stale_periods} periods"}
    if s.get("mountinfo_hung"):
        return {"allow": False, "latch": True, "host": True, "reason": "the mount table could not be read in time (mountinfo hung)"}
    td = s.get("teardown_counts") or {}
    since = td_base or {}             # the counts are cumulative: what a person has already looked at and reset does not latch again
    td = {k: td.get(k, 0) - since.get(k, 0) for k in ("held", "abort_failed")}
    if td.get("held") or td.get("abort_failed"):
        return {"allow": False, "latch": True, "host": True,
                "reason": f"a teardown could not release a FUSE mount: {td.get('held', 0)} held, {td.get('abort_failed', 0)} failed aborts"}
    if s.get("d_unlisted"):
        return {"allow": False, "latch": True, "host": True, "reason": f"D-state build-up: {s['d_tasks']} tasks in D, more than a sample lists"}
    pd = persistent_d(samples, rule.persist_samples)
    if pd is None or s.get("d_tasks") is None:
        return {"allow": False, "latch": False, "host": False, "reason": "D states unreadable"}
    # kernel threads (jbd2, writeback workers: in D whenever the disk is busy, as at rest on this host) are recorded, not counted. In a FUSE wait
    # channel: a user-space task outside the containers (dockerd, runc, a mount helper) is the stronger sign, and an unknown cgroup counts as the host
    fuse = stuck_on_fuse(samples, rule.persist_samples)
    host = [t for t in fuse if t.get("in_container") is not True]
    cont = [t for t in fuse if t.get("in_container") is True]
    if len(host) >= rule.host_d_max:
        return {"allow": False, "latch": True, "host": True,
                "reason": f"D-state build-up: {len(host)} host tasks in a FUSE wait for {rule.persist_samples} samples",
                "tasks": host[:16]}
    if len(cont) >= rule.container_d_max:
        return {"allow": False, "latch": True, "host": True,
                "reason": f"D-state build-up: {len(cont)} container tasks in a FUSE wait for {rule.persist_samples} samples",
                "tasks": cont[:16]}
    long = persistent_d(samples, rule.other_persist_samples)
    if long is None:
        return {"allow": False, "latch": False, "host": False, "reason": "D states unreadable"}
    counted = {(t["tid"], t["comm"]) for t in fuse}       # whatever the FUSE rule did not take, a task that only just reached FUSE included
    others = [t for t in long if (t["tid"], t["comm"]) not in counted and not t.get("kthread")]
    if len(others) >= rule.other_d_max:
        return {"allow": False, "latch": True, "host": True,
                "reason": f"D-state build-up: {len(others)} tasks in other wait channels for {rule.other_persist_samples} samples",
                "tasks": others[:16]}
    mem = s.get("mem_available_bytes")
    if mem is None:
        return {"allow": False, "latch": False, "host": False, "reason": "MemAvailable unreadable"}
    if mem < rule.mem_min_gib * GIB:
        return {"allow": False, "latch": False, "host": True, "reason": f"MemAvailable {mem / GIB:.1f} GiB below {rule.mem_min_gib} GiB"}
    return {"allow": True, "latch": False, "host": False, "reason": None}


class DispatchGate:
    """`allow_more()`: may one more sandbox start now? Evaluated on every sample and at every call; latched closed at the
    first D-state build-up (or a hung mount table) until `reset()`; the transition is written to the sampler's file."""

    def __init__(self, sampler: HostSampler, rule: GateRule = GateRule()):
        self.sampler, self.rule = sampler, rule
        self._lock = threading.Lock()
        self.latched: bool = False
        self.reason: str | None = "no sample yet"
        self.host_closed: bool = False       # the last closure came from what the host showed, not from not knowing
        self.latched_detail: dict | None = None
        self._td_base: dict = {}             # the teardown counts at the last reset
        sampler.on_sample(lambda _s: self._update())

    def _update(self) -> bool:
        d = evaluate(self.sampler.recent(max(self.rule.persist_samples, self.rule.other_persist_samples, 1)), self.rule, time.monotonic(), self.sampler.period_s, self._td_base)
        with self._lock:
            if self.latched:
                self.host_closed = True
                return False
            self.host_closed = d["host"]
            if d["latch"]:
                self.latched, self.reason, self.latched_detail = True, d["reason"], d
                self.sampler.write({"kind": "gate", "event": "latched", "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                                    "reason": d["reason"], "tasks": d.get("tasks")})
                return False
            if d["reason"] != self.reason:
                self.sampler.write({"kind": "gate", "event": "open" if d["allow"] else "closed",
                                    "utc": dt.datetime.now(dt.timezone.utc).isoformat(), "reason": d["reason"]})
            self.reason = d["reason"]
            return d["allow"]

    def allow_more(self) -> bool:
        return self._update()

    def reset(self) -> None:
        """For a person, after looking at the host: clears the latch."""
        with self._lock:
            self.latched, self.latched_detail = False, None
            newest = self.sampler.recent(1)
            self._td_base = dict((newest[-1].get("teardown_counts") or {}) if newest else {})
        self.sampler.write({"kind": "gate", "event": "reset", "utc": dt.datetime.now(dt.timezone.utc).isoformat()})


# ------------------------------------------------------------------------------------------------ the ramp
@dataclasses.dataclass(frozen=True)
class Ticket:
    level: int
    index: int


class StepRamp:
    """Concurrency in steps: `level` starts at levels[0]; after `min_completed` runs dispatched at the current level have
    completed, it steps to the next level if the gate is open. Once the gate has closed for something the host showed (a
    build-up, the memory floor; at any check), it never steps again (`halted` records the level and the reason). A gate
    closed for not knowing (no sample yet, a stale or unreadable one) holds dispatch and the step, without a halt: a slow
    scan under load is not a finding about the level. Dispatch also waits for the gate."""

    def __init__(self, gate, levels: tuple[int, ...] = (4, 8, 12, 16), min_completed: int = 4,
                 on_event: Callable[[dict], None] | None = None):
        if not levels or list(levels) != sorted(set(levels)) or levels[0] < 1:
            raise ValueError(f"levels must be increasing positive integers: {levels}")
        if min_completed < 1:
            raise ValueError("min_completed must be at least 1")
        self.gate, self.levels, self.min_completed = gate, tuple(levels), int(min_completed)
        self._i, self._done, self._n = 0, 0, 0
        self.halted: dict | None = None
        self._lock = threading.Lock()
        self._event = on_event or (lambda e: None)

    @property
    def level(self) -> int:
        return self.levels[self._i]

    def _gate_open(self) -> bool:
        ok = self.gate.allow_more()
        if not ok and self.halted is None and getattr(self.gate, "host_closed", True):
            self.halted = {"level": self.level, "reason": getattr(self.gate, "reason", None)}
            self._event({"event": "ramp_halted", **self.halted})
        return ok

    def may_dispatch(self, in_flight: int) -> bool:
        with self._lock:
            return in_flight < self.level and self._gate_open()

    def dispatched(self) -> Ticket:
        with self._lock:
            self._n += 1
            return Ticket(self.level, self._n)

    def completed(self, ticket: Ticket) -> None:
        with self._lock:
            if ticket.level != self.level:
                return                     # dispatched at an earlier level: it says nothing about this one
            self._done += 1
            if self._done < self.min_completed or self._i + 1 >= len(self.levels) or self.halted is not None:
                return
            if self._gate_open():
                self._i, self._done = self._i + 1, 0
                self._event({"event": "ramp_step", "level": self.level})
