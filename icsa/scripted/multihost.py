"""The concurrency curve across two run hosts (science, #34, 2 Nov 14:32Z): one contiguous upward search in two sittings.

Levels up to the local host's capacity run on it alone, as `python -m icsa.scripted curve` runs a level. Higher levels run on both
hosts at once: the level's slots are dealt between them, each host runs its share (`curve-part`), and one level barrier spans both
(the launcher starts every sandbox's read only after BOTH hosts have every sandbox of their share up). The level is then decided
once, by curve.py's rule, over the union of both hosts' records and the single-run baselines. The curve's levels are TOTAL sandboxes,
and site_g's load is shared.

    python -m icsa.scripted curve-multi --out DIR --block B --baseline DIR.. --hosts FILE --capacity a=N,b=M [--levels ..] [--resume]
    python -m icsa.scripted curve-part  --out DIR --block B --level L --slots i,j,k --host NAME ...        (what the launcher starts)

`curve-part` runs ONLY its host's share and decides nothing. The launcher (on the local host) starts the remote part through the
campaign's transport (`icsa.campaign.hosts`, the forced command of `icsa.campaign.remote`), waits for both `ready` markers, sets `go`
on both (the remote host's first, so a stalled call cannot let the local host read alone), waits for both parts, pulls the remote part's
directory back, and decides.

A level whose part fails, times out, or cannot be reached is NOT decided: it is recorded as an infrastructure failure of the level
(`passed: false`, `infrastructure` set) and the search stops. A resume runs such a level again; it never counts as a pass.

The duty-cycle form (`--duty-profile`, as `curve` takes it) runs the batch's own `run_mix` under its Pacer on each host, for that host's slots of
`plans.duty_slots`: both hosts start from the same `go` after the barrier, each slot's seeded offset and fixed cycle running from the moment its host
passed it. Each part records every run's planned and actual start; a host whose measured cycles began further than GO_SKEW_LIMIT_S from the plan makes the
level an infrastructure failure. The profile's hash is on every decision line and in the state file, and a resume or a part under another is refused.

M's idle waits (science, #34, 22:16Z). A counted run that waited IDLE for an M slot (`extra.m_deferral.idle_s` above 1 s: only M cells were left and its
host was at its share of M users, so the slot held no sandbox) caps the level's offered load like a wait for the pacer's guards: the level does not pass.
`duty.apply_verdict` writes that, once, for this launcher and `cmd_curve` alike: `failed_on` is "m_bound" when the level would have passed but for those
waits, "not_m_bound" for any other failing level, and absent on a pass; `m_bound_waits` lists the runs. A level that failed on M's bound while running on ONE host is
rerun once, here only: the same level and profile, split across both hosts in proportion to their capacities, where it has all the M users (`rerun_blocker`
says when it may; a level already split had them all, so it stands). The rerun's line (`rerun_of`, `first_part_id`) decides the level, pass or fail; the first
line is kept, and a resume reads from the file that the rerun was made. An infrastructure failure of the rerun is no measurement and does not use it up.
Nothing in `curve --resume` is confused by the extra line: `curve.decided_levels` takes the later one. `curve-multi --resume` also picks up the level of a
one-host `curve` sitting that failed on M's bound (no `hosts` field means it ran on one host), unless the split offers no more M users than that sitting had,
or the provider-state / profile / baseline checks refuse.

A part cannot outlive its launcher: while a split level runs the launcher touches `hb-<n>` on both hosts, and a part whose newest heartbeat is
older than `--heartbeat-timeout` (or whose parent process changed) stops its padding and starts no new counted run, from its own local files only.

Levels above 16 need `--above-16-decision <URL>` naming science's ruling (recorded in the state file and in every decision line); the ceiling is
the smallest of the two capacities' sum, `--max-level` and 42 (plans.DUTY_MAX_LEVEL = 3 x M's 16 x 0.875, science #34 17:22Z; above it needs a later ruling, decision named or not). M's 16-mount cap
holds inside a level's mix by M skip-ahead (`mgate.py`): each host keeps its M sandboxes at its share of M slot users (the shares partition the 16),
running a slot's next non-M cell first when its M cell would exceed it. The decision line carries the level's measured M report.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses
import hashlib
import importlib
import contextlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
import types
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .. import opwrestart
from ..sandbox import termination
from . import curve as Cv
from . import duty as DC
from . import mgate, plans

RUNNER_ENV = "ICSA_SCRIPTED_PART_RUNNER"     # tests only: "module:factory", THIS host's own setting like ICSA_REMOTE_EXECUTOR, never taken from argv
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")      # a host name becomes part of marker names (remote.MARKER_RE: at most 64 characters)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REPO = Path(__file__).resolve().parents[2]
PART_RESULT = "part_result.json"
PART_LOG = "part.log"
DEFAULT_BARRIER_TIMEOUT_S = 1800.0           # as the level barrier of a one-host level (runner.py)
DEFAULT_PADDING_TIMEOUT_S = 8 * 3600.0       # an orphaned part pads at most this long after its own counted runs: a slot's four runs at the 2 h cap
DEFAULT_PART_TIMEOUT_S = 10 * 3600.0
LEASE_WAIT_LIMIT_S = 1.0     # a paced level's run that waited longer for its slot user ran later than its sandbox was counted as up: not the stated
                             # concurrency (review of f42b726, finding 3); fixed before the curve runs
GO_SKEW_LIMIT_S = 5.0        # the most the two hosts' sandboxes may differ in when they passed the barrier (each by its own, NTP-synced clock), else the level
                             # is an infrastructure failure, never a pass. Fixed here, before the curve runs: not a setting to tune after seeing a result.
DEFAULT_HEARTBEAT_S = 30.0                  # the launcher touches `hb-<n>` on both hosts this often while a split level runs
DEFAULT_HEARTBEAT_TIMEOUT_S = 180.0         # a part whose newest heartbeat is older than this stops its padding: the launcher is gone
PART_FAIL_RC = 1
PART_BARRIER_BROKEN_RC = 3


class LevelInfra(Exception):
    """The level could not be run to a decision: not a pass, and not a result of the rule."""

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind, self.detail = kind, detail


# ---- the split: pure -----------------------------------------------------------------------------------------------------
def parse_capacity(text: str, names: list[str]) -> dict[str, int]:
    """"a=12,b=8" -> {"a": 12, "b": 8}: both hosts of the host file, each at least 1."""
    caps: dict[str, int] = {}
    for part in text.split(","):
        k, sep, v = part.partition("=")
        k = k.strip()
        if not sep or k in caps or not v.strip().isdigit() or int(v) < 1:
            raise SystemExit(f"--capacity {text!r}: expected NAME=N for each host, N a whole number of at least 1")
        caps[k] = int(v)
    if sorted(caps) != sorted(names):
        raise SystemExit(f"--capacity {text!r}: the hosts of the host file are {sorted(names)}")
    return caps


def split_counts(level: int, cap_local: int, cap_remote: int, force_split: bool = False) -> tuple[int, int]:
    """(slots on the local host, slots on the remote one). Up to the local capacity everything runs locally; above it the level is
    split in proportion to the capacities, rounding in the local host's favour (it never exceeds either capacity while level <= sum).
    `force_split` (the M-bound rerun): the proportional split even though the level fits on the local host; refused when it puts nothing on the remote one."""
    if level < 1:
        raise ValueError(f"level {level}: must be at least 1")
    if level <= cap_local and not force_split:
        return level, 0
    if level > cap_local + cap_remote:
        raise ValueError(f"level {level} exceeds the capacities {cap_local} + {cap_remote}")
    n_local = -(-level * cap_local // (cap_local + cap_remote))
    if force_split and level - n_local < 1:
        raise ValueError(f"level {level}: the proportional split of capacities {cap_local} : {cap_remote} puts nothing on the remote host")
    return n_local, level - n_local


def deal(level: int, n_local: int, n_remote: int, n_instances: int = 1) -> tuple[list[int], list[int]]:
    """The level's slots 0..level-1 to the two hosts, round-robin in the ratio of their counts: the host furthest behind its share takes the
    next slot, a tie going to the local host (equal counts alternate local, remote, ..). A slot's instance is slot-plus-run modulo the
    instances, so with several instances the slots are dealt class by class (slot modulo the instances), which gives each host each instance
    in its share of the level; with one instance this is the plain deal, slot by slot."""
    if n_local + n_remote != level:
        raise ValueError(f"{n_local} + {n_remote} slots for level {level}")
    m = max(1, n_instances)
    order = [k for r in range(m) for k in range(r, level, m)]
    loc: list[int] = []
    rem: list[int] = []
    for j, k in enumerate(order):
        behind_local = n_local * (j + 1) - level * len(loc)
        behind_remote = n_remote * (j + 1) - level * len(rem)
        if len(loc) < n_local and (len(rem) >= n_remote or behind_local >= behind_remote):
            loc.append(k)
        else:
            rem.append(k)
    return sorted(loc), sorted(rem)


@dataclasses.dataclass
class LevelPlan:
    level: int
    counts: dict[str, int]
    slots: dict[str, list[int]]
    multi: bool
    forced: bool = False             # the M-bound rerun: split although the level fits on the local host

    def record(self) -> dict:
        return {"counts": dict(self.counts), "slots": {h: list(v) for h, v in self.slots.items()}, "multi": self.multi, **({"forced_split": True} if self.forced else {})}


def deal_modulus(n_instances: int, n_cells: int, duty: bool) -> int:
    """What a slot's mix depends on, modulo: its instance (slot number modulo the instances) and, in the duty-cycle plan, its cell (the cells are handed out
    along the slot numbers), so the deal gives each host each instance and each cell in its share. The flat plan's cell orders are random per slot."""
    return math.lcm(n_instances, n_cells) if duty else n_instances


def plan_level(level: int, local: str, remote: str, caps: dict[str, int], n_instances: int = 1, force_split: bool = False) -> LevelPlan:
    n_local, n_remote = split_counts(level, caps[local], caps[remote], force_split)
    loc, rem = deal(level, n_local, n_remote, n_instances)
    counts, slots = {local: n_local}, {local: loc}
    if n_remote:
        counts[remote], slots[remote] = n_remote, rem
    return LevelPlan(level, counts, slots, multi=bool(n_remote), forced=force_split)


# ---- the host file --------------------------------------------------------------------------------------------------------
@dataclasses.dataclass
class HostFile:
    local: str
    remote: str
    specs: dict[str, Any]                  # name -> icsa.campaign.hosts.HostSpec
    scripted_root: str                     # where the remote host keeps scripted dirs (its ICSA_REMOTE_SCRIPTED_ROOT)

    def names(self) -> list[str]:
        return [self.local, self.remote]


def load_hosts(path: str | Path) -> HostFile:
    """{"a": {"remote": false, "slot_keys": [..]}, "b": {"remote": true, "ssh": [..], "scripted_root": "..", "slot_keys": [..]}}: the shape of the
    campaign's `hosts`, plus the remote host's scripted root. Exactly one local and one remote host."""
    from ..campaign import hosts as HH
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise SystemExit(f"--hosts {path}: {e}")
    if not isinstance(raw, dict) or len(raw) != 2:
        raise SystemExit(f"--hosts {path}: expected two hosts (one local, one remote), got {sorted(raw) if isinstance(raw, dict) else raw!r}")
    roots: dict[str, str] = {}
    cleaned: dict[str, dict] = {}
    for name, d in raw.items():
        if not NAME_RE.match(name) or not isinstance(d, dict):
            raise SystemExit(f"--hosts {path}: host name {name!r} must match {NAME_RE.pattern} and hold an object")
        d = dict(d)
        root = d.pop("scripted_root", None)
        if root is not None:
            roots[name] = str(root)
        cleaned[name] = d
    try:
        specs = HH.host_specs(types.SimpleNamespace(hosts=cleaned))
    except HH.HostConfigError as e:
        raise SystemExit(f"--hosts {path}: {e}")
    loc = [n for n, s in specs.items() if not s.remote]
    rem = [n for n, s in specs.items() if s.remote]
    if len(loc) != 1 or len(rem) != 1:
        raise SystemExit(f"--hosts {path}: exactly one host must be local and one remote (local {loc}, remote {rem})")
    if not specs[rem[0]].ssh:
        raise SystemExit(f"--hosts {path}: remote host {rem[0]!r} has no ssh command")
    root = roots.get(rem[0])
    if not root or not os.path.isabs(root):
        raise SystemExit(f"--hosts {path}: remote host {rem[0]!r} needs an absolute scripted_root (its ICSA_REMOTE_SCRIPTED_ROOT)")
    both = set(specs[loc[0]].slot_keys) & set(specs[rem[0]].slot_keys)
    if both:
        raise SystemExit(f"--hosts {path}: slot keys {sorted(both)} are on both hosts: a slot user must never be held on both")
    return HostFile(loc[0], rem[0], specs, root.rstrip("/"))


# ---- markers ---------------------------------------------------------------------------------------------------------------
def atomic_marker(d: Path, name: str) -> float:
    """`<d>/marker-<name>` holding this host's time, created whole (the remote `marker --set` does the same on its host)."""
    d.mkdir(parents=True, exist_ok=True)
    t = time.time()
    tmp = d / f"marker-{name}.tmp"
    tmp.write_text(f"{t}\n")
    os.replace(tmp, d / f"marker-{name}")
    return t


def marker_time(d: Path, name: str) -> float | None:
    try:
        return float((d / f"marker-{name}").read_text().strip())
    except (OSError, ValueError):
        return None


def _write_json(path: Path, obj: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=str))
    os.replace(tmp, path)


# ---- one host's part -------------------------------------------------------------------------------------------------------
class LevelBarrier(threading.Barrier):
    """The level's barrier on this host, remembering when each sandbox got through it."""

    def __init__(self, parties: int, action: Callable[[], None] | None = None):
        super().__init__(parties, action)
        self.passed: list[float] = []
        self._plock = threading.Lock()

    def wait(self, timeout: float | None = None) -> int:
        i = super().wait(timeout)
        with self._plock:
            self.passed.append(time.time())
        return i


def go_action(d: Path, host: str, timeout_s: float, state: dict, lost: threading.Event | None = None) -> Callable[[], None]:
    """Runs once, when every sandbox of this host's share is up: says so (`ready-<host>`), then waits for the launcher's `go`. Running out of
    time raises BrokenBarrierError, which breaks the barrier: every run records 'barrier broken', as in a one-host level."""
    def action() -> None:
        state["ready_epoch"] = atomic_marker(d, f"ready-{host}")
        deadline = time.monotonic() + timeout_s
        while marker_time(d, "go") is None:
            if termination.requested() or (lost is not None and lost.is_set()):
                raise threading.BrokenBarrierError("terminated, or the launcher's heartbeat was lost, while waiting for go")
            if time.monotonic() >= deadline:
                state["go_timeout"] = True
                raise threading.BrokenBarrierError(f"no go within {timeout_s:g} s of ready")
            time.sleep(0.05)
        state["go_seen_epoch"] = time.time()
    return action


def newest_heartbeat(d: Path) -> float | None:
    """When the newest `marker-hb-<n>` in `d` was written, by THIS host's clock (the file's own time); None when there is none. Local files only: a
    part never asks the network whether its launcher is alive."""
    best = None
    for f in d.glob("marker-hb-*"):
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        best = m if best is None or m > best else best
    return best


class PartControl:
    """What keeps one host's share of a level in step with its launcher, for the flat and the paced form alike: the flags `state`, the events
    (`lost`: the launcher is gone, nothing new starts; `stop`: padding ends; `counted_done`), the `go` handshake, and the watcher thread that reads
    only this host's own files and pid (the launcher's `stop` marker, its heartbeat, the parent process, the padding time-out). `solo`: the whole
    level is on this host, which ends its own padding and needs no watcher."""

    def __init__(self, out: Path, host: str, *, solo: bool, barrier_timeout_s: float, padding_timeout_s: float, heartbeat_timeout_s: float,
                 parent_pid: int | None):
        self.out, self.host, self.solo = out, host, solo
        self.barrier_timeout_s, self.padding_timeout_s, self.heartbeat_timeout_s = barrier_timeout_s, padding_timeout_s, heartbeat_timeout_s
        self.ppid0 = os.getppid() if parent_pid is None else parent_pid
        self.state: dict[str, Any] = {"ready_epoch": None, "go_seen_epoch": None, "go_timeout": False, "stop_by": None, "padding_timeout": False,
                                      "heartbeat_lost": False, "parent_died": False}
        self.lost = threading.Event()
        self.counted_done = threading.Event()
        self.stop = self.counted_done if solo else threading.Event()
        self.broken: Callable[[], bool] = lambda: False     # whether the level's barrier is broken: the flat form sets its own barrier's
        self.pass_epoch: float | None = None
        self._thread: threading.Thread | None = None

    def go_action(self) -> Callable[[], None]:
        return go_action(self.out, self.host, self.barrier_timeout_s, self.state, self.lost)

    def dead(self) -> bool:
        return termination.requested() or (not self.solo and (self.broken() or self.lost.is_set()))

    def rendezvous(self) -> float:
        """The paced form's barrier: this host is ready, and waits for the launcher's `go` (it says it to both hosts, the remote one first). Returns
        the moment this host passed it: the paced schedule's anchor, by this host's own clock. Time-out or a lost launcher break it."""
        broken = [False]
        self.broken = lambda: broken[0]
        if not self.solo:
            try:
                self.go_action()()
            except threading.BrokenBarrierError:
                broken[0] = True
                raise
        self.pass_epoch = time.time()
        return self.pass_epoch

    def start_watcher(self) -> None:
        if not self.solo:
            self._thread = threading.Thread(target=self._watch, name="stop-watcher", daemon=True)
            self._thread.start()

    def finish(self) -> None:
        self.stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _watch(self) -> None:
        st, stop = self.state, self.stop
        t_done = None
        t_watch = time.time()
        tick = 0
        while not stop.wait(0.25):
            tick += 1
            if termination.requested() or self.broken():
                st["stop_by"] = "terminated" if termination.requested() else "barrier broken"
                stop.set()
                return
            if marker_time(self.out, "stop") is not None:
                st["stop_by"] = "launcher"
                stop.set()
                return
            if os.getppid() != self.ppid0:
                st["parent_died"], st["stop_by"] = True, "parent died"
                self.lost.set()
                stop.set()
                return
            if self.heartbeat_timeout_s > 0 and tick % 4 == 0:
                newest = max(newest_heartbeat(self.out) or 0.0, t_watch)
                if time.time() - newest > self.heartbeat_timeout_s:
                    st["heartbeat_lost"], st["stop_by"] = True, "heartbeat lost"
                    self.lost.set()
                    stop.set()
                    return
            if self.counted_done.is_set():
                t_done = time.monotonic() if t_done is None else t_done
                if time.monotonic() - t_done > self.padding_timeout_s:
                    st["padding_timeout"], st["stop_by"] = True, "padding timeout"
                    stop.set()
                    return


class RealRunner:
    """A part's sandbox runs: the batch's own `run_one`, with the plan's instance, its reference hash and this host's sandbox configuration."""
    name = None

    def __init__(self, M, recs, truth, refs, cfg, target):
        self.M, self.recs, self.truth, self.refs, self.cfg, self.target = M, recs, truth, refs, cfg, target

    def run(self, plan, out_dir: Path, **kw) -> dict:
        from . import federation as F
        return self.M.run_one(plan, self.recs[plan.instance_id], self.truth, lambda o=plan.option: F.data_config(self.target, o), self.cfg,
                              out_dir, expected_sst=self.refs[plan.instance_id], **kw)

    def m_share(self) -> int:
        return mgate.host_m_share()

    def mix(self, *, block, level, rep, out, **kw) -> list[dict]:
        """The paced form's level on this host: the batch's own `run_mix`, with this host's data."""
        return self.M.run_mix(block, level, rep, self.recs, self.truth, self.refs, self.cfg, out, target=self.target, **kw)

    def max_live(self, n_slots: int, per_run_gib: float) -> int:
        """The most sandboxes this host's memory holds at once (as `cmd_curve` takes it for the duty-cycle curve); the pacer caps the level there."""
        from . import metrics
        fit = Cv.levels_that_fit(range(1, n_slots + 1), metrics.meminfo_available_gib(), per_run_gib)
        return max(fit) if fit else 0

    def kills(self, since: float) -> list[dict] | None:
        from ..sandbox import earlyoom as EO
        ks = EO.read_kills(since)
        return None if ks is None else [k.record() for k in ks]


def parse_refs(text: str, instances: tuple[str, ...]) -> dict[str, str]:
    """"I35=<sha256>,.." -> {instance: sha256}: the launcher's reference hashes, so that a host needs no s1z copy; every instance must be there."""
    out: dict[str, str] = {}
    for part in text.split(","):
        k, _, v = part.partition("=")
        if k in out or not HEX64.match(v):
            raise SystemExit(f"--refs: {part[:20]!r} is not INSTANCE=<64 hex characters>, or repeats an instance")
        out[k] = v
    missing = [i for i in instances if i not in out]
    if missing:
        raise SystemExit(f"--refs lacks {missing}")
    return out


def _resolve(spec: str) -> Callable:
    mod, _, fn = spec.partition(":")
    if not mod or not fn:
        raise SystemExit(f"{RUNNER_ENV}={spec!r}: expected module:factory")
    return getattr(importlib.import_module(mod), fn)


def _say(host: str, r: dict) -> None:
    print(f"{time.strftime('%H:%M:%SZ', time.gmtime())} [{host}] {r.get('run_key')} ok={r.get('ok')} wall={r.get('wall_s')}", flush=True)


def _padding_failed(r: dict) -> bool:
    """Any padding run that did not end ok, except one cancelled because the counted runs had finished: a padding run that failed early (its
    script stopped at the listing, say) loaded site_g less than the level says, so the level's measurement is not a full level's (review delta, 3f3a582)."""
    if any(str(e).startswith("cancelled:") for e in (r.get("errors") or [])):
        return False
    return bool(r.get("infrastructure")) or not r.get("ok")


def run_part(runner, *, out: Path, block: int, level: int, rep: int, seed: int, instances: tuple[str, ...], ids: list[int], host: str,
             solo: bool, barrier_timeout_s: float, padding_timeout_s: float, heartbeat_timeout_s: float = 0.0, parent_pid: int | None = None,
             max_level: int = plans.MAX_LEVEL) -> dict:
    """This host's share of one level: the slots `ids` of the level's plan, which is built whole (`plans.mix_slots`: the draws run through all
    slots in order, so a share is cut from the full plan, never planned alone), with the level's number in every record and the padding's
    own generator keyed by the global slot. Structure as `run_mix`: each slot goes through its counted runs, then pads until told to stop.

    `solo`: the whole level is on this host: the barrier is local and ends the padding when its own counted runs end, exactly as a one-host
    level. Otherwise the level's barrier also waits for the other host (`ready-<host>`, then `go` from the launcher), and padding stops
    only when the launcher says both hosts' counted runs are done (`stop`), so that every counted run on either host saw the full level.

    A dead-man's switch for the split case, so that a part cannot outlive its launcher and keep loading site_g: the launcher touches `marker-hb-<n>` in
    this directory while the level runs, and when the newest one is older than `heartbeat_timeout_s` (0: no check; the first beat is due within one
    timeout of the part's start), or the parent process changed (the launcher, or the remote worker, died), the part stops padding and starts no new
    counted run. Runs in flight finish. The part is then not complete. It reads only its own files and pid, never the network.
    Returns what happened; the result is written to part_result.json by the caller."""
    all_slots = plans.mix_slots(seed, block, level, rep, instances, max_level=max_level)
    gate = mgate.gate_for(block, level, runner.m_share() if mgate.active(level) else None)     # above 16: this host's M share (None at or below)
    n = len(ids)
    runs = out / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    ctl = PartControl(out, host, solo=solo, barrier_timeout_s=barrier_timeout_s, padding_timeout_s=padding_timeout_s,
                      heartbeat_timeout_s=heartbeat_timeout_s, parent_pid=parent_pid)
    state, lost, counted_done, stop = ctl.state, ctl.lost, ctl.counted_done, ctl.stop
    barrier = LevelBarrier(n, None if solo else ctl.go_action())
    ctl.broken = lambda: barrier.broken
    lock = threading.Lock()
    remaining = [n]
    counts = {"counted": 0, "padding": 0}
    errors: list[str] = []
    padding_failures: list[str] = []
    dead = ctl.dead

    def slot_fn(k: int) -> None:
        base = {"level": level, "rep": rep, "block": block, "slot": k, "host": host, **({"runner": runner.name} if runner.name else {})}
        try:
            for i, p, gx in mgate.cells(gate, k, all_slots[k]):
                if dead():
                    return
                r = runner.run(p, runs, barrier=barrier if i == 0 else None, extra={**base, **gx} if gx else base)
                if gate is not None:
                    gate.note(r)
                _say(host, r)
                with lock:
                    counts["counted"] += 1
        except BaseException as e:      # noqa: BLE001 - recorded; the finally lets the others finish
            with lock:
                errors.append(f"slot {k}: {type(e).__name__}: {e}"[:500])
            raise
        finally:
            with lock:
                remaining[0] -= 1
                last = not remaining[0]
            if last:
                if not solo:
                    atomic_marker(out, f"counted-{host}")
                counted_done.set()
        rng = np.random.default_rng([seed, block, level, rep, k])
        j = 0
        while not stop.is_set() and not dead():
            p = plans.padding_plan(rng, block, level, rep, k, j, instances)
            j += 1
            gx = {}
            if gate is not None:
                ok, gx = gate.padding_start(p)
                if not ok:                      # an M cell beyond this host's share: the next draw
                    continue
            try:
                r = runner.run(p, runs, extra={**base, "padding": True, **gx}, cancel=stop)
            finally:
                if gate is not None:
                    gate.padding_end(p)
            if gate is not None:
                gate.note(r)
            with lock:
                counts["padding"] += 1
                if _padding_failed(r):                  # a padding sandbox that did not start (or hit infrastructure) left this host lighter than the level says
                    padding_failures.append(f"{r.get('run_key')}: {(r.get('errors') or ['?'])[0]}"[:300])

    t0 = time.time()
    ctl.start_watcher()
    with cf.ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(slot_fn, k) for k in ids]
    ctl.finish()
    for f in futures:
        e = f.exception()
        if e is not None and not any(str(e)[:60] in x for x in errors):
            errors.append(f"{type(e).__name__}: {e}"[:500])
    kills = runner.kills(t0)
    broken = bool(not solo and (barrier.broken or state["go_timeout"]))
    res = {"host": host, "block": block, "level": level, "rep": rep, "solo": solo, "slots": list(ids), "n_local": n, "t0_epoch": t0, "t1_epoch": time.time(),
           "ready_epoch": state["ready_epoch"], "go_seen_epoch": state["go_seen_epoch"],
           "barrier_passed_epoch": [min(barrier.passed), max(barrier.passed)] if barrier.passed else None,
           "barrier_broken": broken, "go_timeout": state["go_timeout"], "stop_by": state["stop_by"],
           "padding_timeout": state["padding_timeout"], "heartbeat_lost": state["heartbeat_lost"], "parent_died": state["parent_died"],
           "counted_runs": counts["counted"], "padding_runs": counts["padding"],
           "padding_failures": padding_failures, "earlyoom_kills": kills, "errors": errors, "runner": runner.name, "m_gate": None if gate is None else gate.report(host)}
    res["complete"] = (not errors and not padding_failures and not res["barrier_broken"] and not res["padding_timeout"] and not res["heartbeat_lost"] and not res["parent_died"]
                       and counts["counted"] == sum(len(all_slots[k]) for k in ids)
                       and not termination.requested())
    return res


# ---- the duty-cycle (paced) form -----------------------------------------------------------------------------------------------
PROFILE_FILE = "duty_profile.json"     # in each part's own directory: the local part's written by the launcher, the remote one's carried in its start spec
MAX_PROFILE_BYTES = 4 << 20             # a given-shares profile carries a provenance string per cell; far below this, and no argv limit applies


def profile_text(prof: dict) -> str:
    """The frozen profile as the file each part reads (canonical JSON). It travels with the part, never as an argument (the lead, 2 Nov: a
    given-shares profile's provenance can pass the forced command's 4096-character argument limit); its hash travels beside it."""
    t = json.dumps(prof, sort_keys=True)
    if len(t.encode()) > MAX_PROFILE_BYTES:
        raise SystemExit(f"the duty profile is {len(t.encode())} bytes, above {MAX_PROFILE_BYTES}: refused")
    return t


def load_profile_file(path: str, expected_id: str, *, block: int, instances: tuple[str, ...], seed: int, traced: bool) -> dict:
    """A part's profile: the body must hash to the profile id the launcher names (the first sitting's, on every decision line), and be made for
    this run. A body that is another profile than the named one is refused, never run."""
    try:
        prof = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise SystemExit(f"--duty-profile-file {path}: not a readable profile: {e}")
    if not isinstance(prof, dict) or prof.get("format") != DC.FORMAT or prof.get("profile_id") != DC.profile_id(prof):
        raise SystemExit("--duty-profile-file: not a duty profile, or its body does not match its own profile id")
    if prof["profile_id"] != expected_id:
        raise SystemExit(f"--duty-profile-file: the profile's hash {prof['profile_id'][:12]}.. is not the {expected_id[:12]}.. this level is judged against: refused")
    want = {"block": block, "instances": list(instances), "seed": seed, "traced": traced}
    diff = {k: (prof.get(k), v) for k, v in want.items() if prof.get(k) != v}
    if diff:
        raise SystemExit(f"--duty-profile-file: made for another run ((profile, now): {diff})")
    return prof


_SLOT_RE = re.compile(r"-s(\d+)-n\d+")


class RecordingPacer(DC.Pacer):
    """The batch's Pacer, unchanged, with what this host's schedule did written down, for the cycle starts a part reports: each slot's seeded offset,
    and for every run the moment it was due to start (`intent`: before any wait for the pacer's guards), the moment it did (`start`), when it ended
    and the gap the Pacer then asked for. The guard's answer also carries the two start times into the run's own record (`extra.pace_wait_s`)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.rows: dict[str, dict] = {}
        self.offsets: dict[int, float] = {}
        self._rlock = threading.Lock()

    @staticmethod
    def _slot(plan) -> int:
        m = _SLOT_RE.search(plan.key())
        return int(m.group(1)) if m else -1

    def offset_s(self, plan, rng) -> float:
        v = super().offset_s(plan, rng)
        with self._rlock:
            self.offsets[self._slot(plan)] = v
        return v

    @contextlib.contextmanager
    def guard(self, plan, wait: bool = True):
        intent = time.time()
        with super().guard(plan, wait) as w:
            if w is None:
                yield None
                return
            row = {"slot": self._slot(plan), "tag": plan.tag, "intent": intent, "start": time.time(), "end": None, "gap": None, "rec": None}
            with self._rlock:
                self.rows[plan.key()] = row
            try:
                yield {**w, "intent_epoch": row["intent"], "start_epoch": row["start"]}
            finally:
                row["end"] = time.time()

    def gap_s(self, plan, rng, rec) -> float:
        g = super().gap_s(plan, rng, rec)
        row = self.rows.get(plan.key())
        if row is not None:
            row["gap"] = g
            row["rec"] = rec
        return g


def cycle_schedule(rows: dict[str, dict], offsets: dict[int, float], t0: float) -> list[dict]:
    """Each run's planned start against its actual one, per slot, from the anchor `t0` (the moment this host passed the barrier, by its own clock). The
    first run of a slot (its warm-up) is due at t0 + the slot's seeded offset; each next run one whole cycle after, as the Pacer holds it: what the previous
    run took (the wait for the guards, then the run) plus the gap the Pacer asked for. A run that overran its cycle is not drift: its gap is 0, and the next
    run is due when it ends. `drift_s` is how late the run began against that, and it accumulates: a host whose starts slip a little each cycle shows it."""
    by_slot: dict[int, list[dict]] = {}
    for key, r in rows.items():
        by_slot.setdefault(r["slot"], []).append({"run_key": key, **r})
    out: list[dict] = []
    for slot, runs in sorted(by_slot.items()):
        runs.sort(key=lambda r: r["intent"])
        planned: float | None = t0 + offsets.get(slot, 0.0)
        for i, r in enumerate(runs):
            if i:
                q = runs[i - 1]
                planned = None if planned is None or q["gap"] is None or q["end"] is None else planned + (q["end"] - q["intent"]) + q["gap"]
            kind = "counted" if r["tag"].startswith("mix-") else ("warmup" if i == 0 else "padding")
            out.append({"slot": slot, "run_key": r["run_key"], "kind": kind, "planned_epoch": planned, "intent_epoch": r["intent"], "start_epoch": r["start"],
                        "guard_wait_s": round(r["start"] - r["intent"], 3), "gap_s": r["gap"],
                        "drift_s": None if planned is None else round(r["intent"] - planned, 3)})
    return out


def drift_summary(schedule: list[dict]) -> dict:
    """The largest drift over the measured cycles (the warm-up and the counted runs; padding after them only fills the level until it ends)."""
    measured = [r for r in schedule if r["kind"] in ("warmup", "counted") and r["drift_s"] is not None]
    worst = max(measured, key=lambda r: abs(r["drift_s"]), default=None)
    return {"limit_s": GO_SKEW_LIMIT_S, "max_abs_s": None if worst is None else abs(worst["drift_s"]),
            "worst": None if worst is None else {"slot": worst["slot"], "run_key": worst["run_key"], "drift_s": worst["drift_s"]},
            "measured_starts": len(measured), "unplanned": sum(1 for r in schedule if r["kind"] in ("warmup", "counted") and r["drift_s"] is None)}


class PacedPart:
    """What `run_mix` asks of a host's share of a paced level (its `part` hook), over this host's `PartControl`."""

    def __init__(self, ctl: PartControl, host: str, ids: list[int], runner_name: str | None):
        self.ctl, self.host, self.slot_ids = ctl, host, list(ids)
        self.stop = None if ctl.solo else ctl.stop            # split: the launcher's `stop` ends padding; solo: this host's own end, as `cmd_curve`
        self.extra = {"host": host, **({"runner": runner_name} if runner_name else {})}
        self.t0: float | None = None

    def start(self) -> None:
        self.t0 = self.ctl.rendezvous()

    def counted_done(self) -> None:
        if not self.ctl.solo:
            atomic_marker(self.ctl.out, f"counted-{self.host}")
        self.ctl.counted_done.set()

    def dead(self) -> bool:
        return self.ctl.dead()


def paced_m_quota(max_m_runs: int, shares: dict[str, int]) -> dict[str, int]:
    """Each host's share of the profile's M limit in a split paced level (review of f42b726, finding 1: each part's own Pacer held the whole limit, so
    the hosts together could exceed it). In proportion to the hosts' M slot users, largest remainders, never above a host's users, and at least one
    each, since a host with none could not run its M cells: a limit that cannot give every host one is refused."""
    hs = sorted(shares)
    total = sum(shares.values())
    if total <= 0 or any(shares[h] <= 0 for h in hs):
        raise SystemExit(f"a host of {hs} has no M slot user ({shares}): a split paced level with M cannot run there")
    cap = min(int(max_m_runs), total)
    if cap < len(hs):
        raise SystemExit(f"the profile's M limit {max_m_runs} cannot give each of {hs} one M sandbox: a split paced level is refused")
    raw = {h: cap * shares[h] / total for h in hs}
    q = {h: min(shares[h], max(1, int(raw[h]))) for h in hs}
    for h in sorted(hs, key=lambda h: (raw[h] - int(raw[h]), h), reverse=True):
        if sum(q.values()) >= cap:
            break
        if q[h] < shares[h]:
            q[h] += 1
    while sum(q.values()) > cap:                       # the at-least-one floor can overshoot: take back from the largest
        h = max(hs, key=lambda h: (q[h], h))
        q[h] -= 1
    return q


def pacer_profile(prof: dict, m_quota: int | None) -> dict:
    """The profile as this host's Pacer sees it: the same body and id, its M limit this host's quota (a split level), never above the profile's."""
    if m_quota is None or int(m_quota) >= int(prof["max_m_runs"]):
        return prof
    return {**prof, "max_m_runs": int(m_quota)}


def missing_warmups(schedule: list[dict], ids: list[int]) -> list[int]:
    """Slots of this part whose warm-up did not run (review of f42b726, finding 2): their first counted run began from cold, so the level is not as planned."""
    return sorted(set(ids) - {r["slot"] for r in schedule if r["kind"] == "warmup"})


def lease_wait_failures(rows: dict) -> list[str]:
    """Runs that waited longer than LEASE_WAIT_LIMIT_S for their slot user (review of f42b726, finding 3): the level was not at its stated concurrency
    for that time, which the Pacer did not see. A run with no slot-user lease (`onedata_slot` absent: another token source) waited for none."""
    out = []
    for k, row in sorted(rows.items()):
        w = ((row.get("rec") or {}).get("onedata_slot") or {}).get("wait_s")
        if w is not None and float(w) > LEASE_WAIT_LIMIT_S:
            out.append(f"{k}: waited {float(w):.1f} s for its slot user")
    return out


def level_rows(pacer_rows: dict, done: list) -> dict:
    """Every run of the part with its own record: the pacer keeps one only through a run's gap, which the run that ends the level never takes, so
    the counted runs' records come from the mix itself (delta pass on d90cb55, finding 1)."""
    return {**pacer_rows, **{r["run_key"]: {**pacer_rows.get(r["run_key"], {}), "rec": r} for r in done if r and r.get("run_key")}}


def run_part_duty(runner, *, out: Path, block: int, level: int, rep: int, seed: int, instances: tuple[str, ...], ids: list[int], host: str,
                  solo: bool, barrier_timeout_s: float, padding_timeout_s: float, prof: dict, per_run_gib: float, heartbeat_timeout_s: float = 0.0,
                  parent_pid: int | None = None, m_quota: int | None = None) -> dict:
    """This host's share of one duty-cycle level: the batch's `run_mix` under its Pacer, for the slots `ids` of `plans.duty_slots`, which is built whole and cut
    by global slot number, exactly as the flat form cuts `mix_slots`. Nothing is forked: the host's slots start when both hosts have been released together
    (`PacedPart.start`: ready, then the launcher's `go`), and each slot's offset and fixed cycle run from that moment on this host's clock.

    A paced level has padding too (run-and-gap, behind the Pacer's guards): a slot that has done its counted runs goes on until the level ends, and the level
    ends on both hosts together as the flat form does: this host writes `counted-<host>` when its counted runs are done and pads until the launcher's `stop`
    (solo: until its own counted runs are done). The dead-man's switch is the flat form's, the same `PartControl`.
    The result carries every run's planned and actual start (`cycle_starts`) and the largest drift (`cycle_drift`): the launcher refuses a level whose
    measured cycles began further from the plan than `GO_SKEW_LIMIT_S`."""
    all_slots = plans.duty_slots(seed, block, level, rep, instances)
    n = len(ids)
    runs = out / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    ctl = PartControl(out, host, solo=solo, barrier_timeout_s=barrier_timeout_s, padding_timeout_s=padding_timeout_s,
                      heartbeat_timeout_s=heartbeat_timeout_s, parent_pid=parent_pid)
    pacer = RecordingPacer(pacer_profile(prof, m_quota), level=level, rep=rep, max_live=runner.max_live(n, per_run_gib))
    part = PacedPart(ctl, host, ids, runner.name)
    errors: list[str] = []
    done: list[dict] = []
    gate_report: dict = {}
    hw = DC.HostWatch(pacer)
    t0 = time.time()
    ctl.start_watcher()
    try:
        with hw:
            done = runner.mix(block=block, level=level, rep=rep, out=runs, seed=seed, instances=instances, mem_per_run_gib=per_run_gib, pace=pacer,
                              gate_report=gate_report, part=part)
    except Exception as e:   # noqa: BLE001 - a failed share is a result: recorded, the launcher decides
        errors.append(f"{type(e).__name__}: {e}"[:500])
    finally:
        ctl.finish()
    host_watch = hw.summary()
    kills = runner.kills(t0)
    st = ctl.state
    broken = bool(not solo and (ctl.broken() or st["go_timeout"]))
    schedule = cycle_schedule(pacer.rows, pacer.offsets, part.t0) if part.t0 is not None else []
    padding_failures = [f"{k}: {(row['rec'].get('errors') or ['?'])[0]}"[:300] for k, row in sorted(pacer.rows.items())
                        if not row["tag"].startswith("mix-") and row["rec"] is not None and _padding_failed(row["rec"])]
    no_warmup = missing_warmups(schedule, ids)
    lease_waits = lease_wait_failures(level_rows(pacer.rows, done))
    res = {"host": host, "block": block, "level": level, "rep": rep, "solo": solo, "slots": list(ids), "n_local": n, "t0_epoch": t0, "t1_epoch": time.time(),
           "ready_epoch": st["ready_epoch"], "go_seen_epoch": st["go_seen_epoch"], "barrier_passed_epoch": None if part.t0 is None else [part.t0, part.t0],
           "barrier_broken": broken, "go_timeout": st["go_timeout"], "stop_by": st["stop_by"], "padding_timeout": st["padding_timeout"],
           "heartbeat_lost": st["heartbeat_lost"], "parent_died": st["parent_died"], "counted_runs": len(done),
           "padding_runs": sum(1 for r in schedule if r["kind"] != "counted"), "padding_failures": padding_failures, "earlyoom_kills": kills, "errors": errors,
           "runner": runner.name, "m_gate": gate_report or None, "duty_profile_id": pacer.id, "anchor_epoch": part.t0, "offsets": {str(k): v for k, v in pacer.offsets.items()},
           "cycle_starts": schedule, "cycle_drift": drift_summary(schedule), "cycle_overruns": pacer.overruns, "host_watch": host_watch,
           "m_quota": m_quota, "warmups_missing": no_warmup, "lease_waits": lease_waits}
    res["complete"] = (not errors and not padding_failures and not no_warmup and not lease_waits and not res["barrier_broken"] and not res["padding_timeout"] and not res["heartbeat_lost"]
                       and not res["parent_died"] and len(done) == sum(len(all_slots[k]) for k in ids) and not termination.requested())
    return res


def add_arguments(name: str, s: argparse.ArgumentParser) -> None:
    s.add_argument("--block", type=int, required=True, choices=sorted(plans.BLOCK_CELLS))
    s.add_argument("--instances", default=",".join(plans.BASELINE_INSTANCES))
    s.add_argument("--untraced", action="store_true", help="plain runs, for the comparison only")
    s.add_argument("--rep", type=int, default=1)
    s.add_argument("--mem-per-run-gib", type=float, default=None,
                   help="default: the baselines' largest measured run (agent + gate + sidecar peaks) x 1.15")
    s.add_argument("--barrier-timeout", type=float, default=DEFAULT_BARRIER_TIMEOUT_S,
                   help="seconds: the launcher waits this long for both hosts to be ready, and a part for its `go` after being ready")
    s.add_argument("--heartbeat-timeout", type=float, default=DEFAULT_HEARTBEAT_TIMEOUT_S,
                   help="a part whose newest launcher heartbeat is older than this many seconds stops its padding and starts no new counted run (0: off); "
                        "that level is not complete")
    s.add_argument("--above-16-decision", default=None, help="the decision (URL) of science's ruling that allows levels above 16; recorded in the state file and in every decision line")
    s.add_argument("--padding-timeout", type=float, default=DEFAULT_PADDING_TIMEOUT_S,
                   help="an orphaned part stops padding this long after its own counted runs ended, whether or not `stop` came (that level is then not complete)")
    if name == "curve-part":
        s.add_argument("--level", type=int, required=True)
        s.add_argument("--slots", required=True, help="this host's slots of the level, comma-separated (global numbers)")
        s.add_argument("--m-quota", type=int, default=None, help="the paced form, a split level: this host's share of the profile's M limit (paced_m_quota)")
        s.add_argument("--host", required=True)
        s.add_argument("--solo", action="store_true", help="the whole level is on this host: no ready/go/stop, as a one-host level")
        s.add_argument("--refs", default="", help="INSTANCE=sha256,.. the launcher's SST reference hashes (the host needs no s1z copy)")
        s.add_argument("--run-sha", default="", help="the launcher's ICSA_RUN_SHA, recorded in this part's manifest")
        s.add_argument("--image", default="", help="the launcher's ICSA_SANDBOX_IMAGE tag")
        s.add_argument("--audit-log", default="", help="the launcher's ICSA_AUDIT_LOG state (it must be on)")
        s.add_argument("--duty-profile-file", default="", help="the paced form: the frozen profile, as the launcher copied it into this part's directory")
        s.add_argument("--duty-profile-id", default="", help="the paced form: the hash of the profile this level is judged against; the profile's own must be it")
    else:
        s.add_argument("--baseline", nargs="+", required=True, help="the results directories holding the single runs")
        s.add_argument("--levels", default=",".join(map(str, Cv.DEFAULT_LEVELS)), help="strictly ascending: the search goes upward")
        s.add_argument("--stop", choices=("first-pass", "first-fail", "none"), default="first-fail")
        s.add_argument("--max-level", type=int, default=None, help=f"never run a level above this; default and limit {plans.MAX_LEVEL}")
        s.add_argument("--dry-run", action="store_true", help="print the upward plan with each level's split and exit")
        s.add_argument("--resume", action="store_true", help="after an interruption or in the next sitting: decided levels are not run again")
        s.add_argument("--kill-stale", action="store_true",
                       help="with --resume: stop parts of an earlier attempt that still run (otherwise they refuse the resume), and confirm they are gone")
        s.add_argument("--duty-profile", default=None, metavar="PATH",
                       help="the duty-cycle curve: a profile frozen by duty-profile (given or measured shares), as `curve --duty-profile` takes it; use a new --out")
        s.add_argument("--host-reference-ratios", default=None, metavar="FILE",
                       help="JSON (format icsa-host-reference-ratios-v1): each non-reference host's runs are judged against the reference host's baselines times the file's "
                            "per-cell ratios (wall and read phase apart); absent, every run against --baseline as before. The reference host must be the local host of "
                            "--hosts, whose own runs the baselines are. One file per --out: a resume gives the same one")
        s.add_argument("--hosts", required=True, help="JSON: the two hosts, in the shape of the campaign's `hosts` (+ the remote one's scripted_root)")
        s.add_argument("--capacity", required=True, help="a=N,b=M: each host's sandboxes at once (the capacity benchmark's safe level)")
        s.add_argument("--split", choices=("proportional",), default="proportional")
        s.add_argument("--poll-s", type=float, default=1.0, help="how often the launcher looks for ready, between the start and go")
        s.add_argument("--run-poll-s", type=float, default=5.0, help="how often it looks at the parts while they run")
        s.add_argument("--heartbeat-s", type=float, default=DEFAULT_HEARTBEAT_S, help="how often it touches a heartbeat marker on both hosts while a split level runs")
        s.add_argument("--lost-s", type=float, default=600.0, help="the remote host unreachable for this long: the level is an infrastructure failure")
        s.add_argument("--part-timeout", type=float, default=DEFAULT_PART_TIMEOUT_S, help="seconds from go to both parts done")


# ---- the part's command ------------------------------------------------------------------------------------------------------
def _main_mod(M):
    return M if M is not None else importlib.import_module("icsa.scripted.__main__")


def cmd_curve_part(args, M=None) -> None:
    ppid0 = os.getppid()                                   # the process that started this part: if it changes, the launcher (or the remote worker) is gone
    out = Path(args.out)
    if not NAME_RE.match(args.host):
        raise SystemExit(f"--host {args.host!r}: must match {NAME_RE.pattern}")
    decision = args.above_16_decision or None
    hard_max = plans.DUTY_MAX_LEVEL if decision else plans.MAX_LEVEL
    if not 1 <= args.level <= hard_max:
        raise SystemExit(f"--level {args.level}: must be 1..{hard_max}" + ("" if decision else f" (above {plans.MAX_LEVEL}: --above-16-decision)"))
    try:
        ids = [int(x) for x in args.slots.split(",")]
    except ValueError:
        raise SystemExit(f"--slots {args.slots!r}: expected whole numbers, comma-separated")
    if not ids or len(set(ids)) != len(ids) or min(ids) < 0 or max(ids) >= args.level:
        raise SystemExit(f"--slots {args.slots}: must be distinct numbers in 0..{args.level - 1}")
    instances = plans.parse_instances(args.instances)
    traced = not args.untraced
    out.mkdir(parents=True, exist_ok=True)
    spec = os.environ.get(RUNNER_ENV)
    t_start = time.time()
    res: dict | None = None
    finish: Callable[[], None] = lambda: None   # noqa: E731
    prof = None
    try:
        if bool(args.duty_profile_file) != bool(args.duty_profile_id):
            raise SystemExit("--duty-profile-file and --duty-profile-id go together")
        if args.duty_profile_file:                           # the paced form: refused unless this is the profile the launcher names
            prof = load_profile_file(args.duty_profile_file, args.duty_profile_id, block=args.block, instances=instances, seed=args.seed, traced=traced)
            if not plans.DUTY_MIN_LEVEL <= args.level <= plans.DUTY_MAX_LEVEL:
                raise SystemExit(f"--level {args.level}: the duty-cycle ladder is {plans.DUTY_MIN_LEVEL}..{plans.DUTY_MAX_LEVEL}")
        if spec:                                           # a test's stand-in runner: nothing real is touched (no docker, no federation, no journal)
            runner = _resolve(spec)(args)
            _write_json(out / "MANIFEST_curve_part.json", {"command": "curve-part", "host": args.host, "level": args.level, "slots": ids,
                                                           "runner": spec, "above_16_decision": decision, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        else:
            M = _main_mod(M)
            for flag, env in (("run_sha", "ICSA_RUN_SHA"), ("image", "ICSA_SANDBOX_IMAGE"), ("audit_log", "ICSA_AUDIT_LOG")):
                if getattr(args, flag):
                    os.environ[env] = getattr(args, flag)
            from ..sandbox import earlyoom as EO
            from ..sandbox.termination import wait_for_stop
            EO.require_driver_exempt()
            M.require_audit_log("curve-part")
            from . import federation as F
            from . import metrics
            if args.mem_per_run_gib is None or not 0 < args.mem_per_run_gib < float("inf"):
                raise SystemExit("--mem-per-run-gib: a finite number above zero is required (the launcher takes it from the baselines)")
            man, recs, truth = M._common(args)
            refs = parse_refs(args.refs, instances)
            slot, tracer = F.traced_slot() if traced else (None, None)
            m = M._manifest(out, f"curve_part_{args.host}_c{args.level}", resume=False, seed=args.seed, block=args.block, level=args.level, slots=ids,
                            host=args.host, instances=instances, traced=traced, tracer=tracer, solo=args.solo, mem_per_run_gib=args.mem_per_run_gib,
                            above_16_decision=decision)
            cfg = F.sandbox_config(F.MAIN, m["image"], instruments=slot)
            if prof is None:           # the paced form checks disk and memory in `run_mix` itself, and lets its pacer cap the sandboxes up instead of refusing
                need = plans.disk_needed_gib(args.block, len(ids), F.MAIN.s2_bytes) + M.DISK_MARGIN_GIB
                free = metrics.disk_free_gib(cfg.work_root)
                if free < need:
                    raise SystemExit(f"block {args.block} level {args.level} on {args.host}: {free:.0f} GiB free on the work disk, needs {need:.0f}")
                avail = metrics.meminfo_available_gib()
                if avail < len(ids) * args.mem_per_run_gib + Cv.MEM_RESERVE_GIB:
                    raise SystemExit(f"block {args.block} level {args.level} on {args.host}: {avail:.0f} GiB MemAvailable is too low for {len(ids)} slots "
                                     f"({args.mem_per_run_gib} GiB per run + {Cv.MEM_RESERVE_GIB})")
            runner = RealRunner(M, recs, truth, refs, cfg, F.MAIN)

            def finish() -> None:
                from .runner import cleanup_own_containers
                wait_for_stop(600)                           # the leftovers are what the SIGTERM's own stops did not remove
                left = cleanup_own_containers()
                if left:
                    print(f"removed leftover containers: {left}", file=sys.stderr)
        if prof is not None:
            if args.mem_per_run_gib is None or not 0 < args.mem_per_run_gib < float("inf"):
                raise SystemExit("--mem-per-run-gib: a finite number above zero is required (the launcher takes it from the baselines)")
            res = run_part_duty(runner, out=out, block=args.block, level=args.level, rep=args.rep, seed=args.seed, instances=instances, ids=ids, host=args.host,
                                solo=args.solo, barrier_timeout_s=args.barrier_timeout, padding_timeout_s=args.padding_timeout, prof=prof,
                                per_run_gib=args.mem_per_run_gib, heartbeat_timeout_s=args.heartbeat_timeout, parent_pid=ppid0, m_quota=args.m_quota)
        else:
            res = run_part(runner, out=out, block=args.block, level=args.level, rep=args.rep, seed=args.seed, instances=instances, ids=ids, host=args.host,
                           solo=args.solo, barrier_timeout_s=args.barrier_timeout, padding_timeout_s=args.padding_timeout,
                           heartbeat_timeout_s=args.heartbeat_timeout, parent_pid=ppid0, max_level=hard_max)
    except BaseException as e:
        _write_json(out / PART_RESULT, {"host": args.host, "level": args.level, "slots": ids, "complete": False, "t0_epoch": t_start,
                                        "errors": [f"{type(e).__name__}: {e}"[:500]]})
        raise
    finally:
        finish()
    _write_json(out / PART_RESULT, res)
    print(json.dumps({k: res[k] for k in ("host", "level", "complete", "counted_runs", "padding_runs", "barrier_broken", "stop_by")}), flush=True)
    if not res["complete"]:
        raise SystemExit(PART_BARRIER_BROKEN_RC if res["barrier_broken"] else PART_FAIL_RC)


# ---- the launcher -----------------------------------------------------------------------------------------------------------
class _Part:
    """One host's share of a level, as the launcher drives it. `dir` is where its records end up on THIS host."""

    def __init__(self, host: str, dir: Path, ids: list[int]):
        self.host, self.dir, self.ids = host, dir, ids
        self.finished = False


class LocalPart(_Part):
    remote = False

    def start(self, argv: list[str], slot_keys: list[str], files: dict[str, str] | None = None) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        for name, text in (files or {}).items():
            (self.dir / name).write_text(text)
        env = dict(os.environ)
        if slot_keys:
            env["ICSA_SLOT_KEYS"] = ",".join(slot_keys)
        log = open(self.dir / PART_LOG, "ab")
        try:
            self.proc = subprocess.Popen([sys.executable, "-m", "icsa.scripted", *argv], stdin=subprocess.DEVNULL, stdout=log, stderr=log, cwd=str(REPO), env=env,
                                         start_new_session=True)       # its own process group: a stale part can be stopped as a group (`reconcile_stale`)
        finally:
            log.close()

    def has(self, name: str) -> bool:
        return marker_time(self.dir, name) is not None

    def set(self, name: str) -> float:
        return atomic_marker(self.dir, name)

    def beat(self, n: int) -> None:
        atomic_marker(self.dir, f"hb-{n}")

    def state(self) -> tuple[str, int | None]:
        rc = self.proc.poll()
        return ("running", None) if rc is None else ("done", rc)

    def kill(self, grace_s: float = 120.0) -> None:
        if self.proc.poll() is not None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(grace_s)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(30)

    def fetch(self, best_effort: bool = False) -> None:
        return None


class RemotePart(_Part):
    remote = True

    def __init__(self, host: str, dir: Path, ids: list[int], remote_dir: str, transport, lost_s: float, poll_s: float,
                 mono: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep):
        super().__init__(host, dir, ids)
        self.rdir, self.t, self.lost_s, self.poll_s, self._mono, self._sleep = remote_dir, transport, lost_s, poll_s, mono, sleep
        self._down_since: float | None = None
        self._last = ""

    def _call(self, args: list[str], stdin: bytes | None = None, timeout: float = 60.0) -> tuple[int, bytes, bytes] | None:
        """The transport's answer, or None when the host did not answer; unreachable for `lost_s` in a row is the level's infrastructure failure."""
        from ..campaign import hosts as HH
        try:
            got = self.t.call(args, stdin=stdin, timeout=timeout)
        except HH.TransportError as e:
            now = self._mono()
            self._down_since = now if self._down_since is None else self._down_since
            self._last = str(e)
            if now - self._down_since >= self.lost_s:
                raise LevelInfra("host_unreachable", f"{self.host} unreachable for {self.lost_s:g} s ({self._last})") from e
            return None
        self._down_since = None
        return got

    def _must(self, args: list[str], what: str, stdin: bytes | None = None, timeout: float = 60.0) -> tuple[int, bytes, bytes]:
        while True:
            got = self._call(args, stdin, timeout)
            if got is not None:
                return got
            self._sleep(self.poll_s)

    def start(self, argv: list[str], slot_keys: list[str], files: dict[str, str] | None = None) -> None:
        payload = json.dumps({"kind": "scripted", "argv": argv, "slot_keys": list(slot_keys), "host": self.host, "files": files or {}}).encode()
        rc, out, err = self._must(["scripted-start", self.rdir], "start", payload)
        if rc != 0:
            raise LevelInfra("start_failed", f"{self.host}: scripted-start exit {rc}: {(err or b'').decode(errors='replace')[-300:]}")
        try:
            st = json.loads(out).get("state")
        except ValueError:
            st = None
        if st != "started":            # a reused directory would hold the last level's markers: never join one
            raise LevelInfra("start_failed", f"{self.host}: scripted-start answered {st!r}, not 'started' (dir {self.rdir})")

    def has(self, name: str) -> bool:
        got = self._call(["marker", self.rdir, name])
        if got is None:
            return False
        if got[0] not in (0, 1):
            raise LevelInfra("marker_failed", f"{self.host}: marker {name} exit {got[0]}: {(got[2] or b'').decode(errors='replace')[-200:]}")
        return got[0] == 0

    def set(self, name: str) -> float:
        t = time.time()                                    # before the call: the host may act on it any time from then on
        rc, out, err = self._must(["marker", self.rdir, name, "--set"], "marker")
        if rc != 0:
            raise LevelInfra("marker_failed", f"{self.host}: setting marker {name} exit {rc}: {(err or b'').decode(errors='replace')[-200:]}")
        return t

    def beat(self, n: int) -> None:
        """One heartbeat marker on the host, through the same `marker` command (increasing names). Called from this part's own thread, so it touches no
        state of the level's polling: a failure is just a beat the host did not get, and the host's part decides from its own files."""
        self.t.call(["marker", self.rdir, f"hb-{n}", "--set"], timeout=30)

    def state(self) -> tuple[str, int | None]:
        got = self._call(["wait", self.rdir, "--scripted", "--timeout", "0"], timeout=60)
        if got is None:
            return "unknown", None
        rc, out, err = got
        if rc == 3:
            return "running", None
        if rc == 4:
            return "died", None
        if rc == 0:
            try:
                return "done", int(json.loads(out)["rc"])
            except (ValueError, KeyError, TypeError):
                raise LevelInfra("part_failed", f"{self.host}: an unreadable result from wait: {out[:100]!r}") from None
        raise LevelInfra("part_failed", f"{self.host}: wait exit {rc}: {(err or b'').decode(errors='replace')[-200:]}")

    def kill(self, grace_s: float = 120.0) -> None:
        from ..campaign import hosts as HH
        try:
            self.t.call(["kill", self.rdir, "--scripted"], timeout=grace_s + 90)
        except HH.TransportError:
            pass                      # unreachable: nothing more to do from here; the level is recorded as an infrastructure failure either way

    def fetch(self, best_effort: bool = False) -> None:
        from ..campaign import hosts as HH
        try:
            rc, out, err = self.t.call(["pack", self.rdir, "--scripted"], timeout=120 if best_effort else 1800)
            if rc != 0:
                raise LevelInfra("pull_failed", f"{self.host}: pack exit {rc}: {(err or b'').decode(errors='replace')[-200:]}")
            self.dir.mkdir(parents=True, exist_ok=True)
            HH._safe_extract(out, self.dir)
        except (HH.TransportError, HH.RemoteHarnessError, OSError) as e:
            if not best_effort:
                raise LevelInfra("pull_failed", f"{self.host}: the part's directory could not be pulled: {e}") from e
        except LevelInfra:
            if not best_effort:
                raise


def m_shares(hosts: HostFile) -> dict[str, int]:
    """Each host's M share from its slot keys and the slot map (a part computes its own from its environment; the two must agree)."""
    return mgate.m_shares({h: list(s.slot_keys) for h, s in hosts.specs.items()})


def check_m_shares(block: int, lps: dict[int, "LevelPlan"], shares: dict[str, int]) -> None:
    """Above 16, with M among the block's cells: every host that runs slots needs an M slot user (else its M cells cannot run), and the shares of
    the hosts of a level add up to at most 16, M's mount cap."""
    if not shares or not mgate.block_has_m(block):
        return
    for lv, lp in lps.items():
        if not mgate.active(lv):
            continue
        for h, n in lp.counts.items():
            if shares.get(h, 0) < 1:
                raise SystemExit(f"block {block} level {lv}: host {h!r} has no M slot user (its M share is 0), but its {n} slots run M cells: refused")
        total = sum(shares[h] for h in lp.counts)
        if total > mgate.MAX_M_RUNS:
            raise SystemExit(f"block {block} level {lv}: the hosts' M shares {dict((h, shares[h]) for h in lp.counts)} add up to {total}, above M's "
                             f"{mgate.MAX_M_RUNS}-mount cap: the hosts' slot users must partition at most {mgate.MAX_M_RUNS} M users: refused")


class _Beat(threading.Thread):
    """The launcher's heartbeat to one part: a fresh marker every `period_s` while the level runs. One thread per part, so a slow ssh to the remote
    host cannot delay the local beat."""

    def __init__(self, part: _Part, period_s: float):
        super().__init__(name=f"heartbeat-{part.host}", daemon=True)
        self.part, self.period = part, period_s
        self._halt = threading.Event()
        self.sent = 0

    def run(self) -> None:
        n = 0
        while not self._halt.is_set():
            n += 1
            try:
                self.part.beat(n)
                self.sent += 1
            except Exception:       # noqa: BLE001 - not heard is the part's own business; the level's polling decides whether the host is lost
                pass
            self._halt.wait(self.period)

    def halt(self) -> None:
        self._halt.set()
        self.join(timeout=5)


@dataclasses.dataclass
class Ctx:
    args: Any
    M: Any
    out: Path
    hosts: HostFile
    caps: dict[str, int]
    instances: tuple[str, ...]
    cells: list[tuple[str, str]]
    traced: bool
    own: dict
    own_read: dict
    bid: str
    site_g_hash: str
    per_run: float
    refs: dict[str, str]
    image: str | None
    image_id: str | None
    run_sha: str | None
    runner_spec: str | None
    refdet_sha: str
    m_shares: dict = dataclasses.field(default_factory=dict)       # each host's M share (above 16), from the slot map
    decision: str | None = None             # science's ruling that allows levels above 16 (--above-16-decision)
    hard_max: int = plans.MAX_LEVEL
    prof: dict | None = None                # the duty-cycle form: the frozen profile (None: the flat-out form)
    prof_blob: str = ""                     # ... as the parts read it (`profile_text`), copied into each part's directory
    transport: Any = None
    sleep: Callable[[float], None] = time.sleep
    host_ratios: dict | None = None         # science's host reference (--host-reference-ratios): each host's runs judged against its own scaled baseline (None: every run against --baseline)


def _part_argv(ctx: Ctx, host: str, d: str, ids: list[int], level: int, solo: bool) -> list[str]:
    a = ctx.args
    argv = ["curve-part", "--out", d, "--block", str(a.block), "--level", str(level), "--slots", ",".join(map(str, ids)), "--host", host,
            "--seed", str(a.seed), "--rep", str(a.rep), "--instances", ",".join(ctx.instances), "--mem-per-run-gib", repr(ctx.per_run),
            "--barrier-timeout", repr(float(a.barrier_timeout)), "--padding-timeout", repr(float(a.padding_timeout)),
            "--heartbeat-timeout", repr(float(a.heartbeat_timeout))]
    if ctx.decision:
        argv += ["--above-16-decision", ctx.decision]
    if ctx.prof is not None:
        argv += ["--duty-profile-file", f"{d}/{PROFILE_FILE}", "--duty-profile-id", ctx.prof["profile_id"]]
        if not solo:                                  # a split level: this host's share of the profile's M limit (the hosts' sum is the limit)
            shares = m_shares(ctx.hosts)
            argv += ["--m-quota", str(paced_m_quota(int(ctx.prof["max_m_runs"]), {h: shares.get(h, 0) for h in (ctx.hosts.local, ctx.hosts.remote)})[host])]
    if not ctx.traced:
        argv.append("--untraced")
    if solo:
        argv.append("--solo")
    if ctx.refs:
        argv += ["--refs", ",".join(f"{k}={v}" for k, v in sorted(ctx.refs.items()))]
    for flag, v in (("--run-sha", ctx.run_sha), ("--image", ctx.image), ("--audit-log", "on" if not ctx.runner_spec else None)):
        if v:
            argv += [flag, v]
    return argv


def _out_tag(out: Path) -> str:
    import hashlib
    return f"{out.name}-{hashlib.sha256(str(out.resolve()).encode()).hexdigest()[:8]}"


def _remote_dir(ctx: Ctx, part_id: str) -> str:
    return f"{ctx.hosts.scripted_root}/{_out_tag(ctx.out)}/{part_id}-{ctx.hosts.remote}"


# ---- parts of an earlier attempt that are still running ----------------------------------------------------------------------------
def stale_local_parts(out: Path) -> list[tuple[int, str]]:
    """(pid, its part directory) of every live `curve-part` whose `--out` lies in this curve's `parts/`: found by the process's own command line, so a
    part is found whatever its launcher did. A pid that is gone, or is a zombie (no command line), is not live."""
    parts_dir = os.path.realpath(out / "parts") + os.sep
    found = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit() or int(d.name) == os.getpid():
            continue
        try:
            words = [w.decode(errors="replace") for w in (d / "cmdline").read_bytes().split(b"\0")]
        except OSError:
            continue
        if "curve-part" in words and "--out" in words and words.index("--out") + 1 < len(words):
            path = os.path.realpath(words[words.index("--out") + 1])
            if path.startswith(parts_dir):
                found.append((int(d.name), path))
    return sorted(found)


def stale_remote_parts(transport, hosts: HostFile, out: Path) -> list[str]:
    """The remote host's live part directories of this curve, from its own probe (`live`: the dirs with a running worker). A host that cannot be asked is
    not known to be clear: refused."""
    from ..campaign import hosts as HH
    try:
        rc, o, e = transport.call(["probe"], timeout=120)
    except HH.TransportError as ex:
        raise SystemExit(f"curve-multi: host {hosts.remote!r} cannot be reached ({ex}): whether parts of an earlier attempt still run there is not known")
    try:
        if rc != 0:
            raise ValueError(f"probe exit {rc}")
        live = json.loads(o)["live"]
    except (ValueError, KeyError, TypeError) as ex:
        raise SystemExit(f"curve-multi: the probe of host {hosts.remote!r} could not be read ({ex}): whether parts of an earlier attempt still run there is not known")
    return sorted(d for d in live if f"/{_out_tag(out)}/" in d)


def _kill_local(pid: int) -> None:
    for sig, wait_s in ((signal.SIGTERM, 120.0), (signal.SIGKILL, 10.0)):
        try:
            pg = os.getpgid(pid)
            if pg == pid:
                os.killpg(pg, sig)              # the part leads its own group (every part this code starts does)
            else:
                os.kill(pid, sig)               # an older part in its launcher's group: never the group, which holds the launcher
        except ProcessLookupError:
            return
        end = time.monotonic() + wait_s
        while time.monotonic() < end:
            try:
                alive = b"curve-part" in Path(f"/proc/{pid}/cmdline").read_bytes()
            except OSError:
                alive = False
            if not alive:
                return
            time.sleep(0.2)


def reconcile_stale(out: Path, hosts: HostFile, lps: dict[int, "LevelPlan"], transport, *, kill: bool) -> None:
    """On a resume, before any replacement starts: parts of an earlier attempt that still run would finish their current runs while the replacements run the
    same plan keys, so two executions overlap on site_g. Any live one is a refusal that lists it; `--kill-stale` stops them first and confirms they are gone."""
    local = stale_local_parts(out)
    parts_dir = out / "parts"
    check_remote = any(lp.multi for lp in lps.values()) or (parts_dir.is_dir() and any(parts_dir.glob(f"*-{hosts.remote}")))     # a split level ran, or will
    tr = None
    remote: list[str] = []
    if check_remote:
        from ..campaign import hosts as HH
        tr = transport or HH.SshTransport(hosts.specs[hosts.remote].ssh)
        remote = stale_remote_parts(tr, hosts, out)
    if not local and not remote:
        return
    listing = [f"local pid {pid} ({d})" for pid, d in local] + [f"{hosts.remote}: {d}" for d in remote]
    if not kill:
        raise SystemExit("curve-multi: refusing to resume: parts of an earlier attempt are still running, and would overlap the replacements' runs of the same plan keys: "
                         + "; ".join(listing) + ". Wait for them, or pass --kill-stale to stop them first.")
    print(f"curve-multi: stopping {len(listing)} stale parts: {'; '.join(listing)}", flush=True)
    for pid, _ in local:
        _kill_local(pid)
    for d in remote:
        try:
            tr.call(["kill", d, "--scripted"], timeout=300)
        except Exception as ex:   # noqa: BLE001 - confirmed below by the probe, which is what counts
            print(f"curve-multi: kill of {d} on {hosts.remote!r}: {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
    left = [f"local pid {pid} ({d})" for pid, d in stale_local_parts(out)] + ([f"{hosts.remote}: {d}" for d in stale_remote_parts(tr, hosts, out)] if check_remote else [])
    if left:
        raise SystemExit("curve-multi: --kill-stale could not stop: " + "; ".join(left) + ": nothing is started")


def probe_remote(ctx: Ctx, part: RemotePart, n_slots: int) -> None:
    """Before a split level: the remote host runs this code and the pinned image, and has the memory for its share; unknown is not ok."""
    from .. import codestamp
    got = part._must(["probe"] + (["--image", ctx.image_id] if ctx.image_id else []), "probe", timeout=120)
    rc, out, err = got
    if rc != 0:
        raise LevelInfra("probe_failed", f"{part.host}: probe exit {rc}: {(err or b'').decode(errors='replace')[-200:]}")
    try:
        p = json.loads(out)
    except ValueError:
        raise LevelInfra("probe_failed", f"{part.host}: an unreadable probe answer") from None
    mine = codestamp.tree_hash(REPO)
    if p.get("tree") != mine:
        raise LevelInfra("code_differs", f"{part.host} runs other code than the launcher ({str(p.get('tree'))[:12]} vs {mine[:12]})")
    if ctx.image_id and p.get("image_ok") is not True:
        raise LevelInfra("image_missing", f"{part.host}: the pinned image {ctx.image_id[:19]} is not there")
    mem = p.get("mem_available")
    need = (n_slots * ctx.per_run + Cv.MEM_RESERVE_GIB) * 1024 ** 3
    if not isinstance(mem, (int, float)) or mem < need:
        raise LevelInfra("memory", f"{part.host}: MemAvailable {mem!r} B, {n_slots} slots need {need:.0f} B")


def _drive(ctx: Ctx, lp: LevelPlan, parts: dict[str, _Part], info: dict) -> None:
    """Start, barrier, run: raises LevelInfra for anything that is not a clean end of both parts."""
    a = ctx.args
    loc, rem = parts.get(ctx.hosts.local), parts.get(ctx.hosts.remote)
    solo = not lp.multi
    order = [p for p in (rem, loc) if p is not None]           # the remote one first: its start takes the longer
    for p in order:
        p.start(_part_argv(ctx, p.host, getattr(p, "rdir", str(p.dir)), p.ids, lp.level, solo),
                ctx.hosts.specs[p.host].slot_keys, files={PROFILE_FILE: ctx.prof_blob} if ctx.prof is not None else None)
    info["started_epoch"] = time.time()
    beats = [] if solo else [_Beat(p, a.heartbeat_s) for p in parts.values()]      # a split level's parts stop padding if these stop (their dead-man's switch)
    for b in beats:
        b.start()
    try:
        _phases(ctx, lp, parts, info)
    finally:
        for b in beats:
            b.halt()
        info["heartbeats_sent"] = {b.part.host: b.sent for b in beats}


def _phases(ctx: Ctx, lp: LevelPlan, parts: dict[str, _Part], info: dict) -> None:
    """After the start: both hosts ready, go, then both parts to their end."""
    a = ctx.args
    loc, rem = parts.get(ctx.hosts.local), parts.get(ctx.hosts.remote)
    solo = not lp.multi
    mono = time.monotonic

    def check_alive(p: _Part, strict: bool) -> None:
        st, rc = p.state()
        if st == "died":
            raise LevelInfra("part_failed", f"{p.host}: the part's worker ended without a result")
        if st == "done":
            p.finished = True
            if rc != 0 or strict:
                raise LevelInfra("part_failed" if rc != PART_BARRIER_BROKEN_RC else "barrier_broken", f"{p.host}: the part ended with exit {rc}"
                                 + ("" if rc != 0 else " before the level was decided"))

    if not solo:
        deadline = mono() + a.barrier_timeout
        last_alive = mono()
        ready: dict[str, bool] = {p.host: False for p in parts.values()}
        while not all(ready.values()):
            for p in parts.values():
                if not ready[p.host]:
                    ready[p.host] = p.has(f"ready-{p.host}")
            if all(ready.values()):
                break
            if mono() - last_alive >= a.run_poll_s:
                for p in parts.values():
                    check_alive(p, strict=True)
                last_alive = mono()
            if mono() >= deadline:
                raise LevelInfra("not_ready", f"{sorted(h for h, v in ready.items() if not v)} not ready {a.barrier_timeout:g} s after the start")
            ctx.sleep(a.poll_s)
        for p in parts.values():
            check_alive(p, strict=True)
        info["ready_seen_epoch"] = time.time()
        info["go_epoch"] = {}
        for p in (rem, loc):          # the remote host first: if its call stalls, the local host is not released meanwhile (it would read under a lighter load)
            info["go_epoch"][p.host] = p.set("go")
        info["go_gap_s"] = round(info["go_epoch"][loc.host] - info["go_epoch"][rem.host], 3)      # the launcher's own view; the bound is on the parts' pass times (_union)
    stop_set = False
    deadline = mono() + a.part_timeout
    while True:
        for p in parts.values():
            if not p.finished:
                check_alive(p, strict=False)
        if all(p.finished for p in parts.values()):
            break
        if not solo and not stop_set and all(p.finished or p.has(f"counted-{p.host}") for p in parts.values()):
            for p in (loc, rem):
                if not p.finished:
                    p.set("stop")
            stop_set = True
            info["stop_epoch"] = time.time()
        if mono() >= deadline:
            raise LevelInfra("timeout", f"the parts did not end within {a.part_timeout:g} s of the start")
        ctx.sleep(a.run_poll_s)
    for p in parts.values():
        p.fetch()


def _read_part(p: _Part) -> dict:
    try:
        return json.loads((p.dir / PART_RESULT).read_text())
    except (OSError, ValueError):
        raise LevelInfra("part_failed", f"{p.host}: no readable {PART_RESULT} in {p.dir}") from None


def _load_records(p: _Part) -> list[dict]:
    out = []
    for f in sorted((p.dir / "runs").glob("*/run.json")):
        try:
            r = json.loads(f.read_text())
        except ValueError as e:
            raise LevelInfra("record_unreadable", f"{f}: {e}") from None
        if not isinstance(r, dict):
            raise LevelInfra("record_unreadable", f"{f}: not an object")
        out.append(r)
    return out


def _union(ctx: Ctx, lp: LevelPlan, parts: dict[str, _Part], info: dict) -> tuple[list[dict], dict[str, dict], list[dict]]:
    """Both hosts' counted records, checked to be exactly the level's plan and to come from one configuration: the same traced state, token
    source, runner, source hash and provider-state hash on every record of both hosts. A missing, extra or odd record is an infrastructure
    failure of the level, never a pass."""
    a = ctx.args
    all_slots = (plans.mix_slots(a.seed, a.block, lp.level, a.rep, ctx.instances, max_level=ctx.hard_max) if ctx.prof is None
                 else plans.duty_slots(a.seed, a.block, lp.level, a.rep, ctx.instances))
    results = {h: _read_part(p) for h, p in parts.items()}
    allrecs: list[dict] = []
    for h, p in parts.items():
        res = results[h]
        if not res.get("complete") or res.get("barrier_broken") or res.get("errors") or res.get("padding_timeout") or res.get("heartbeat_lost") or res.get("parent_died") or res.get("padding_failures"):
            raise LevelInfra("barrier_broken" if res.get("barrier_broken") else "part_failed",
                             f"{h}: the part is not complete (errors {res.get('errors')}, barrier_broken {res.get('barrier_broken')}, padding_timeout {res.get('padding_timeout')}, "
                             f"heartbeat_lost {res.get('heartbeat_lost')}, parent_died {res.get('parent_died')}, padding_failures {res.get('padding_failures')})")
        recs = _load_records(p)
        for r in recs:
            if (r.get("extra") or {}).get("host") != h:
                raise LevelInfra("record_mismatch", f"{r.get('run_key')} in {h}'s part says host {(r.get('extra') or {}).get('host')!r}")
        allrecs += recs
    counted = Cv.counted(allrecs)
    want = {pl.key(): h for h, ids in lp.slots.items() for k in ids for pl in all_slots[k]}
    got = [r.get("run_key") for r in counted]
    if len(set(got)) != len(got) or set(got) != set(want):
        raise LevelInfra("incomplete", f"counted runs recorded {len(got)} of {len(want)}; missing {sorted(set(want) - set(got))[:4]}, "
                                       f"unexpected {sorted(set(got) - set(want))[:4]}, duplicated {sorted({k for k in got if got.count(k) > 1})[:4]}")
    for r in counted:
        if r["extra"]["host"] != want[r["run_key"]] or int(r["extra"]["level"]) != lp.level:
            raise LevelInfra("record_mismatch", f"{r['run_key']}: recorded on host {r['extra']['host']!r} at level {r['extra'].get('level')}, planned on {want[r['run_key']]!r}")
    expect = {"traced": ctx.traced, "runner": ctx.runner_spec}
    for r in allrecs:
        why = []
        if bool(r["extra"].get("traced")) is not ctx.traced:
            why.append(f"traced {r['extra'].get('traced')!r}")
        if r["extra"].get("runner") != expect["runner"]:
            why.append(f"runner {r['extra'].get('runner')!r}")
        if r.get("site_g_settings_sha256") != ctx.site_g_hash:
            why.append("site_g_settings_sha256 differs from this sitting's or is None")
        if r.get("refdet_source_sha256") != ctx.refdet_sha:
            why.append("refdet_source_sha256 differs")
        if ctx.prof is not None and r["extra"].get("duty_profile") != ctx.prof["profile_id"]:
            why.append(f"duty profile {str(r['extra'].get('duty_profile'))[:12]!r} is not this curve's {ctx.prof['profile_id'][:12]!r}")
        if why:
            raise LevelInfra("configuration_differs", f"{r.get('run_key')} on {r['extra'].get('host')}: {'; '.join(why)}")
    for field in ("host_aliases", "truth_cell_masks_sha256"):       # b's silent fallbacks: no --add-host (site_g by its public address), another frozen truth
        seen = {json.dumps(r.get(field), sort_keys=True) for r in allrecs}
        if len(seen) != 1 or (field == "truth_cell_masks_sha256" and "null" in seen):
            raise LevelInfra("configuration_differs", f"the records of the two hosts do not agree on {field} (or it is unknown): {sorted(seen)[:3]}")
    sources = {(r.get("token") or {}).get("source") for r in allrecs}
    if len(sources) != 1 or None in sources:
        raise LevelInfra("configuration_differs", f"the records of the two hosts do not share one token source: {sorted(map(str, sources))}")
    if lp.multi:                           # one barrier across two hosts: their sandboxes must have passed it together, by each host's own clock
        passed = [res.get("barrier_passed_epoch") for res in results.values()]
        if not all(passed):
            raise LevelInfra("barrier_order", f"a part recorded no barrier pass time: {passed}")
        skew = max(x[1] for x in passed) - min(x[0] for x in passed)
        info["barrier_skew_s"] = round(skew, 3)
        if skew > GO_SKEW_LIMIT_S:
            raise LevelInfra("go_skew", f"the two hosts' sandboxes passed the barrier {skew:.1f} s apart, above {GO_SKEW_LIMIT_S:g} s: one host read under a lighter load")
    if ctx.prof is not None:
        for h, res in results.items():
            if res.get("duty_profile_id") != ctx.prof["profile_id"]:
                raise LevelInfra("configuration_differs", f"{h}: the part paced by profile {str(res.get('duty_profile_id'))[:12]!r}, not this curve's {ctx.prof['profile_id'][:12]!r}")
            drift = res.get("cycle_drift") or {}       # each host's measured cycles must have begun where the plan put them, from its own barrier pass
            worst = drift.get("max_abs_s")
            info.setdefault("cycle_drift_s", {})[h] = worst
            if worst is None and not drift.get("unplanned"):
                raise LevelInfra("cycle_drift", f"{h}: the part recorded no measured cycle start")
            if worst is not None and worst > GO_SKEW_LIMIT_S:
                raise LevelInfra("cycle_drift", f"{h}: a measured cycle began {worst:.1f} s from its planned start (limit {GO_SKEW_LIMIT_S:g} s): {drift.get('worst')}")
            if drift.get("unplanned"):
                raise LevelInfra("cycle_drift", f"{h}: {drift['unplanned']} measured cycle starts have no planned start to compare with")
    for h, p in parts.items():            # a sandbox got through the barrier before this host's `go` was set: the hosts' clocks are not compared, only each host's own
        res, go = results[h], marker_time(p.dir, "go")
        passed = res.get("barrier_passed_epoch")
        if lp.multi and (go is None or not passed or passed[0] < go - 0.001):
            raise LevelInfra("barrier_order", f"{h}: a sandbox passed the barrier at {passed} before its go marker at {go}")
    return counted, results, allrecs


def _m_gate(ctx: Ctx, lp: LevelPlan, results: dict[str, dict], allrecs: list[dict]) -> dict:
    """The level's M report over both hosts' records. The shares are the ones the parts gated by; they must be the launcher's (the slot map's), and more
    M up at once than a host's share (measured from the records) or than 16 in total means the gate did not hold: an infrastructure failure, never a pass."""
    shares = {}
    for h, res in results.items():
        g = res.get("m_gate") or {}
        shares[h] = (g.get("share") or {}).get(h)
        if shares[h] is None or (ctx.m_shares and shares[h] != ctx.m_shares.get(h)):
            raise LevelInfra("m_share_differs", f"{h}: the part gated M at share {shares[h]!r}, the slot map gives {ctx.m_shares.get(h)!r}")
    rep = mgate.m_report(allrecs, shares)
    rep["padding_m_skipped"] = sum((res.get("m_gate") or {}).get("padding_m_skipped", 0) for res in results.values())
    if not rep["within_share"]:
        raise LevelInfra("m_cap_exceeded", f"M sandboxes up at once, measured from the records: {rep['max_concurrent_m']}, shares {shares} (unmeasured {rep['unmeasured']})")
    return rep


def _hoist(parts: dict[str, _Part], runs: Path) -> int:
    """The level's run directories, from each part's directory into `<out>/runs/`, where every batch's records are and the reports read them."""
    todo = [(d, runs / d.name) for p in parts.values() for d in sorted((p.dir / "runs").glob("*")) if d.is_dir()]
    clash = [t.name for _, t in todo if t.exists()]
    if clash:
        raise LevelInfra("hoist_clash", f"{len(clash)} run directories already exist in {runs}: {clash[:3]}")
    runs.mkdir(parents=True, exist_ok=True)
    for src, dst in todo:
        os.replace(src, dst)
    return len(todo)


def _stop_parts(parts: dict[str, _Part], diagnose: bool) -> None:
    for p in parts.values():
        if not p.finished:
            try:
                p.kill()
            except Exception as e:   # noqa: BLE001 - the level is already failing; the other part must still be stopped
                print(f"curve-multi: could not stop the part on {p.host}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
    if diagnose:
        for p in parts.values():
            if p.remote:
                p.fetch(best_effort=True)


def run_level(ctx: Ctx, level: int, rerun: dict | None = None) -> dict:
    """One level: its decision record (`passed` as the rule says), or an infrastructure record (`passed` false, `infrastructure` set). Never raises
    for a failure of the level's own machinery.

    `rerun`: the level's first attempt, a decision line that failed on M's bound while running on one host (`rerun_blocker` says when that is rerunnable).
    The same level, plan and profile run again split across both hosts in proportion to their capacities, where it has all the M slot users. Its line
    carries `rerun_of` and the first attempt's part id (`first_part_id`), also when it is an infrastructure line. The plan is identical, same rep and so
    the same run keys; the attempt's directories are fresh (`-rr` on the part id, on both hosts), and the first attempt's runs, hoisted into `runs/`, move
    to `runs.superseded/` only once the rerun's records are in hand, so `runs/` always holds the level's deciding attempt."""
    a = ctx.args
    lp = plan_level(level, ctx.hosts.local, ctx.hosts.remote, ctx.caps, deal_modulus(len(ctx.instances), len(ctx.cells), ctx.prof is not None),
                    force_split=rerun is not None)
    utc = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    n_before = len(list((ctx.out / "parts").glob(f"b{a.block}-c{level}-r{a.rep}-*-{ctx.hosts.local}"))) if (ctx.out / "parts").is_dir() else 0
    part_id = f"b{a.block}-c{level}-r{a.rep}-{utc}-t{n_before + 1}" + ("-rr" if rerun is not None else "")      # one fresh directory per attempt, on both hosts: a stale marker would release the next barrier at once
    parts: dict[str, _Part] = {}
    info: dict[str, Any] = {"capacity": dict(ctx.caps), **lp.record(), "part_id": part_id}
    if rerun is None:
        moved = Cv.set_aside_partial(ctx.out / "runs", ctx.out / "runs.superseded", a.block, level, a.rep, utc=utc)
        if moved:
            print(f"level {level}: {len(moved)} run directories of an interrupted attempt moved to runs.superseded/", flush=True)

    def stamp() -> dict:
        return {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "block": a.block, "level": level, "rep": a.rep, "traced": ctx.traced,
                "baseline_id": ctx.bid, "site_g_settings_sha256": ctx.site_g_hash, **({"above_16_decision": ctx.decision} if ctx.decision else {}),
                **({"duty_profile_id": ctx.prof["profile_id"]} if ctx.prof is not None else {}),
                **({"host_reference": {k: ctx.host_ratios[k] for k in ("sha256", "source", "reference_host")}} if ctx.host_ratios is not None else {}),
                **({"rerun_of": "m_bound", "first_part_id": (rerun.get("hosts") or {}).get("part_id")} if rerun is not None else {})}
    t0 = time.time()
    try:
        parts[ctx.hosts.local] = LocalPart(ctx.hosts.local, ctx.out / "parts" / f"{part_id}-{ctx.hosts.local}", lp.slots[ctx.hosts.local])
        if lp.multi:
            from ..campaign import hosts as HH
            tr = ctx.transport or HH.SshTransport(ctx.hosts.specs[ctx.hosts.remote].ssh)
            rp = RemotePart(ctx.hosts.remote, ctx.out / "parts" / f"{part_id}-{ctx.hosts.remote}", lp.slots[ctx.hosts.remote],
                            _remote_dir(ctx, part_id), tr, a.lost_s, a.poll_s, sleep=ctx.sleep)
            parts[ctx.hosts.remote] = rp
            probe_remote(ctx, rp, len(rp.ids))
        info["parts_dir"] = str(ctx.out / "parts")
        try:
            _drive(ctx, lp, parts, info)
        except BaseException:
            _stop_parts(parts, diagnose=True)
            raise
        cut = opwrestart.cut_by_restart(t0)
        if cut:        # an infrastructure record, never a pass or a fail: the resume runs the level again whole
            raise LevelInfra("op_worker_restart", cut)
        counted, results, allrecs = _union(ctx, lp, parts, info)
        m_rep = _m_gate(ctx, lp, results, allrecs) if mgate.active(level) else None
        info["ready_epoch"] = {h: r.get("ready_epoch") for h, r in results.items()} if lp.multi else None
        info["barrier_passed_epoch"] = {h: r.get("barrier_passed_epoch") for h, r in results.items()}
        kills: list[dict] | None = []
        for h, r in results.items():
            k = r.get("earlyoom_kills")
            kills = None if (kills is None or k is None) else kills + [{**x, "host": h} for x in k]
        table = Cv.level_table(ctx.own, counted, single_read=ctx.own_read, host_ratios=ctx.host_ratios, duty=ctx.prof is not None)      # the duty-cycle form judges the medians
        row = Cv.cap(table, ctx.cells, [level], ctx.own, ctx.own_read)
        passed = Cv.level_passes(row, level, kills)
        rec = {**stamp(), "passed": passed, "failing_cells": row["failing"].get(level, []), "runs": len(counted),
               "not_clean": sum(not Cv.clean(r) for r in counted), "earlyoom_kills": kills, "hosts": info, **({"m_gate": m_rep} if m_rep else {})}
        if ctx.prof is not None:      # the duty-cycle curve's own rule over both hosts' records, as `cmd_curve` applies it to one host's
            waits = DC.paced_waits(counted)
            rec.update(measured_cycles=plans.duty_cycles(level, len(ctx.cells)), warmup_cycles=1,
                       reads_per_cell={f"{o}/{la}": sum(1 for r in counted if (r["option"], r["layout"]) == (o, la)) for o, la in ctx.cells}, table=table,
                       paced_waits=waits, host={h: r.get("host_watch") for h, r in results.items()},
                       cycle_overruns=[{**x, "host": h} for h, r in results.items() for x in (r.get("cycle_overruns") or [])],
                       cycle_anchor_epoch={h: r.get("anchor_epoch") for h, r in results.items()}, cycle_drift={h: r.get("cycle_drift") for h, r in results.items()})
            DC.apply_verdict(rec, passed, waits, DC.m_idle_waits(counted), DC.level_gaps(counted, a.block, level, a.rep))      # the same function `cmd_curve` calls: guard waits, M's idle waits, a gap in the plan
            rec.update(DC.level_record(ctx.prof, counted, ctx.own_read, info["counts"], lp.multi, ctx.m_shares, host_ratios=ctx.host_ratios))      # and its fields: the ladder, the hosts and M users it ran on, each mount's reads
        if rerun is not None:         # the rerun's records are the level's now: the first attempt's runs leave `runs/` (they stay on disk, in no statistic)
            moved = Cv.set_aside_partial(ctx.out / "runs", ctx.out / "runs.superseded", a.block, level, a.rep, utc=f"first-attempt-{utc}")
            print(f"level {level}: the first attempt's {len(moved)} run directories moved to runs.superseded/ (the rerun decides the level)", flush=True)
        _hoist(parts, ctx.out / "runs")
        return rec
    except LevelInfra as e:
        return {**stamp(), "passed": False, "infrastructure": e.kind, "detail": e.detail[:600], "level_started_epoch": t0, "hosts": info,
                **(DC.level_record(ctx.prof, None, ctx.own_read, info.get("counts") or {}, bool(info.get("multi")), ctx.m_shares, host_ratios=ctx.host_ratios)
                   if ctx.prof is not None else {})}


def _level_lines(path: Path, block: int, rep: int, traced: bool, bid: str) -> dict[int, list[dict]]:
    """Every line of `curve_decisions.jsonl` for this block and rep, per level, in file order (traced state and baseline must match, by curve.py's rule).
    Infrastructure lines are in it: `level_state` ignores them, since none is a measurement."""
    Cv.decided_levels(path, block, rep, traced=traced, baseline=bid)
    out: dict[int, list[dict]] = {}
    try:
        lines = open(path).read().splitlines()
    except OSError:
        return {}
    for ln in lines:
        try:
            r = json.loads(ln)
            if r["block"] == block and r.get("rep", 1) == rep:
                out.setdefault(int(r["level"]), []).append(r)
        except (ValueError, KeyError, TypeError):
            continue
    return out


def level_state(lines: list[dict], can_rerun: Callable[[dict], bool]) -> tuple[str, Any]:
    """Where a level stands, from its lines alone (so it is the same on a resume as in the sitting that wrote them):
    ("decided", passed) | ("rerun", the first attempt's line) | ("open", None).
    An infrastructure line is no measurement: it decides nothing and uses up nothing, so a level whose last line is one is where its measured lines left it.
    The last measured line decides, and a measured RERUN line (`rerun_of`) always does, pass or fail: the M-bound rerun is made once, and that is read from
    here, not from memory. A first attempt that failed on M's bound while running on one host is "rerun" while `can_rerun` says it may be."""
    measured = [r for r in lines if not r.get("infrastructure")]
    if not measured:
        return "open", None
    last = measured[-1]
    if last.get("rerun_of") or last.get("passed"):
        return "decided", bool(last.get("passed"))
    if last.get("failed_on") == "m_bound" and can_rerun(last):
        return "rerun", last
    return "decided", False


def rerun_blocker(ctx: Ctx, first: dict) -> str | None:
    """Why a level that failed on M's bound is NOT rerun (the failure stands), or None when it may be. Science's rule (#34, 22:16Z): one rerun, split across
    both hosts, where the level has all the M users. Only a level that ran on ONE host qualifies: a level already split had all of them, so a rerun gives it
    nothing. The same reasoning, held to the number: the split must offer more M users than the first attempt had (a `curve` line that ran on one host with
    all 16 users gains nothing from a split either), and each host must have some, with the two shares adding up to at most 16."""
    if first.get("failed_on") != "m_bound" or first.get("rerun_of"):
        return "it did not fail on M's bound, or it is itself the rerun"
    if (first.get("hosts") or {}).get("multi"):
        return "it ran on both hosts already, with all the M users: a rerun gives it nothing"
    level = int(first["level"])
    try:
        lp = plan_level(level, ctx.hosts.local, ctx.hosts.remote, ctx.caps, deal_modulus(len(ctx.instances), len(ctx.cells), ctx.prof is not None), force_split=True)
    except ValueError as e:
        return str(e)
    shares = {h: int(ctx.m_shares.get(h, 0)) for h in lp.counts}
    if any(v < 1 for v in shares.values()):
        return f"a host has no M slot user (shares {shares})"
    after = sum(shares.values())
    if after > mgate.MAX_M_RUNS:
        return f"the hosts' M shares {shares} add up to {after}, above M's {mgate.MAX_M_RUNS}-mount cap"
    before = sum(int(v) for v in ((first.get("m_gate") or {}).get("share") or {}).values())
    if after <= before:
        return f"the split has {after} M users, no more than the {before} the level had on one host"
    return None


def provider_state() -> str:
    """site_g's settings hash now: the settings must be the frozen ones, and known."""
    from .. import frsettings
    r = frsettings.check_from_env(required=True)
    if r["state"] != "match" or not r.get("hash"):
        raise SystemExit(f"curve-multi: refusing to start: site_g settings {r['state']} ({r['why']})")
    return r["hash"]


def _has_decisions(path: Path, block: int, rep: int) -> bool:
    """Whether `curve_decisions.jsonl` has any line (a measured one or an infrastructure one) for this block and rep; a missing file or a torn line says no."""
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return False
    for ln in lines:
        try:
            r = json.loads(ln)
            if r["block"] == block and r.get("rep", 1) == rep:
                return True
        except (ValueError, KeyError, TypeError):
            continue
    return False


def check_sitting(out: Path, block: int, rep: int, site_g_hash: str | None, decision: str | None = None, profile_id: str | None = None) -> tuple[Path, str | None]:
    """(the state file, the first sitting's hash or None when this is the first). The two-sitting search is conditional on an unchanged provider
    state (science, #34): a hash that differs, or that either side does not know, refuses to continue."""
    state = out / f"multihost_state_block{block}_rep{rep}.json"
    prior = None
    if state.exists():
        try:
            st = json.loads(state.read_text())
            prior = st["site_g_settings_sha256"]
        except (ValueError, KeyError, TypeError):
            raise SystemExit(f"curve-multi: {state} is unreadable: the first sitting's provider state is not known; use a new --out")
        if st.get("duty_profile_id") != profile_id:         # frozen before the curve starts: a resume under another profile (or none, or one where there was none) is another curve
            raise SystemExit(f"curve-multi: refusing to continue: the duty profile's hash now is {str(profile_id)[:12]!r}, the first sitting's was {str(st.get('duty_profile_id'))[:12]!r} "
                             f"(recorded in {state}): the profile is frozen before the curve starts; restart under a new --out")
        if decision and st.get("above_16_decision") not in (None, decision):
            raise SystemExit(f"curve-multi: --above-16-decision {decision} differs from the {st['above_16_decision']} recorded in {state}: one ruling per curve; use a new --out")
    elif (out / "curve_decisions.jsonl").exists():         # a first sitting that did not write the state file: its runs' hashes say
        from .summarize import load_runs
        hashes = {r.get("site_g_settings_sha256") for r in load_runs(out) if (r.get("extra") or {}).get("block") == block and (r.get("extra") or {}).get("rep") == rep}
        if hashes:
            if len(hashes) != 1:
                raise SystemExit(f"curve-multi: the first sitting's runs carry {len(hashes)} different site_g settings hashes: the provider state was not constant; use a new --out")
            prior = hashes.pop()
            if prior is None:
                raise SystemExit("curve-multi: the first sitting's provider state is not known (its records carry no hash); use a new --out")
    if prior is not None and (site_g_hash is None or prior != site_g_hash):
        raise SystemExit(f"curve-multi: refusing to continue: site_g's settings hash now is {str(site_g_hash)[:12]}.., the first sitting's was {prior[:12]}..; science made the "
                         f"two-sitting search conditional on an unchanged provider state (#34): restart the curve from its first level under a new --out")
    return state, prior


def cmd_curve_multi(args, M=None, transport=None, sleep: Callable[[float], None] = time.sleep) -> None:
    """The two-host curve of one block: see the module's docstring. `transport` (tests): the remote host's Transport."""
    M = _main_mod(M)
    levels = [int(x) for x in args.levels.split(",")]
    decision = args.above_16_decision or None
    hard_max = plans.DUTY_MAX_LEVEL if decision else plans.MAX_LEVEL       # above 16 only with science's ruling named, as the duty-cycle curve does
    if max(levels) > hard_max:
        raise SystemExit(f"levels above {plans.MAX_LEVEL} need an explicit decision from the lane's parent"
                         + (f"; the limit is {plans.DUTY_MAX_LEVEL} (3 x M's {plans.M_MOUNTS_PROVEN} x {plans.M_LOAD_SHARE:g}): above it needs a later ruling, --above-16-decision does not cover it"
                            if decision else " (--above-16-decision)"))
    max_level = plans.MAX_LEVEL if args.max_level is None else args.max_level
    if not 1 <= max_level <= hard_max:
        raise SystemExit(f"--max-level {max_level}: must be 1..{hard_max}")
    if args.heartbeat_s <= 0 or (args.heartbeat_timeout and args.heartbeat_timeout < 3 * args.heartbeat_s):
        raise SystemExit(f"--heartbeat-s {args.heartbeat_s:g} and --heartbeat-timeout {args.heartbeat_timeout:g}: the beat must be above 0 and the timeout at least three beats (or 0)")
    if args.stop == "first-pass":
        raise SystemExit("the curve searches upward and stops at the first failing level (--stop first-fail); first-pass was the old top-down search")
    try:
        levels = Cv.plan_levels(levels, max_level)
    except ValueError as e:
        raise SystemExit(str(e))
    if not levels:
        raise SystemExit(f"no level is at or below --max-level {max_level}")
    hosts = load_hosts(args.hosts)
    caps = parse_capacity(args.capacity, hosts.names())
    over = [lv for lv in levels if lv > sum(caps.values())]
    if over:
        raise SystemExit(f"levels {over} exceed the capacities {caps} (together {sum(caps.values())}): refused")
    try:
        instances = plans.parse_instances(args.instances)
    except ValueError as e:
        raise SystemExit(str(e))
    cells = [(o.value, la.value) for o, la in plans.BLOCK_CELLS[args.block]]
    hr_path, hr = getattr(args, "host_reference_ratios", None), None
    if hr_path is not None:     # science's ruling (#34): the host is in the curve's reference. Loaded and checked against the hosts and this block's cells before anything is written or run
        try:
            hr = Cv.load_host_ratios(hr_path, hosts=hosts.names(), cells=cells)
        except ValueError as e:
            raise SystemExit(f"--host-reference-ratios {hr_path}: {e}")
        if hr["reference_host"] != hosts.local:       # the baselines are the dispatching host's own runs: another reference host would scale the wrong host's runs
            raise SystemExit(f"--host-reference-ratios {hr_path}: reference_host {hr['reference_host']!r} is not the local host {hosts.local!r}: the baselines (--baseline) "
                             f"are the dispatching (local) host's own runs, so the reference host must be {hosts.local!r}")
    traced = not args.untraced
    prof, prof_blob = None, ""
    if args.duty_profile:       # the duty-cycle curve, as `curve --duty-profile` takes it: a frozen profile, its levels the curve's levels, no level dropped for memory
        try:
            prof = DC.load_profile(args.duty_profile, block=args.block, instances=instances, seed=args.seed, traced=traced)
        except (DC.DutyInputError, OSError, ValueError) as e:
            raise SystemExit(f"curve block {args.block}: {e}")
        if [int(x) for x in args.levels.split(",")] != prof["levels"]:
            raise SystemExit(f"curve block {args.block}: --levels {args.levels} differ from the levels frozen in the profile {prof['levels']}")
        if min(levels) < plans.DUTY_MIN_LEVEL:
            raise SystemExit(f"curve block {args.block}: the duty-cycle ladder starts at {plans.DUTY_MIN_LEVEL} (the baselines are level 1): levels {levels}")
        prof_blob = profile_text(prof)
    sequence = prof is not None and (prof.get("climb") is not None or prof.get("floor_level") is not None)     # science, #34, 3 Nov 00:33Z: a climb with step-downs
    floor = prof.get("floor_level") if sequence else None
    if sequence:
        if args.stop != "first-fail":
            raise SystemExit("a profile with a climb and step-downs ends at the first failing climb level (--stop first-fail)")
        climb = [c for c in DC.ladder_of(prof)["climb"] if c in levels or c == floor]
        if not climb:
            raise SystemExit(f"curve block {args.block}: no level of the climb {prof.get('climb')} is at or below --max-level {max_level}")
    lps = {lv: plan_level(lv, hosts.local, hosts.remote, caps, deal_modulus(len(instances), len(cells), prof is not None)) for lv in levels + ([floor] if floor else [])}
    m_share_of = m_shares(hosts) if any(mgate.active(lv) for lv in levels) else {}
    check_m_shares(args.block, lps, m_share_of)
    if any(lp.multi for lp in lps.values()):
        specs = hosts.specs
        if not specs[hosts.local].slot_keys or not specs[hosts.remote].slot_keys:
            raise SystemExit("--hosts: a split level needs slot_keys for both hosts (a lease is an flock, which does not cross hosts: each host leases only its own share)")
    if args.dry_run:
        print(f"curve block {args.block}: upward plan {levels}, stop at the first failing level, cap = the last passing level "
              f"(--max-level {max_level}, hard maximum {hard_max}); nothing is run", flush=True)
        print(f"  ceiling {min(sum(caps.values()), max_level, hard_max)} = min(capacities {sum(caps.values())}, --max-level {max_level}, limit {hard_max})"
              + (f"; above 16 under {decision}" if decision else ""), flush=True)
        if m_share_of:
            print(f"  M shares {m_share_of} (above 16 each host holds its M sandboxes at its share; the shares add up to at most {mgate.MAX_M_RUNS})", flush=True)
        if hr is not None:
            print(f"  host references {hr['sha256'][:12]}..: reference host {hr['reference_host']}, the others' runs judged against its baselines times the file's per-cell ratios; "
                  f"source: {hr['source']}", flush=True)
        if prof is not None:
            print(f"  duty-cycle form, profile {prof['profile_id'][:12]}..: one warm-up cycle and the measured cycles below, paced on both hosts from the barrier", flush=True)
        if sequence:
            print(f"  climb {climb} over the frozen levels {levels}; a failure runs the frozen level below it" + (f", and below {levels[0]} the floor {floor}" if floor else ""), flush=True)
        for lv in levels + ([floor] if floor else []):
            print(f"  level {lv}: {lps[lv].counts}{' (both hosts)' if lps[lv].multi else ' (one host)'}, slots {lps[lv].slots}"
                  + (f", {plans.duty_cycles(lv, len(cells))} measured cycles" if prof is not None else ""), flush=True)
        return
    spec = os.environ.get(RUNNER_ENV) or None
    if not spec:
        M.require_audit_log("curve-multi")
    if args.mem_per_run_gib is not None and not (0 < args.mem_per_run_gib < float("inf")):
        raise SystemExit(f"--mem-per-run-gib {args.mem_per_run_gib}: must be a finite number above zero")
    out = Path(args.out).resolve()           # the parts run from the repo's directory: a relative --out would mean another directory to them
    base = [r for r in M._runs_of(args.baseline) if r["extra"].get("variant", "enforced") == "enforced" and bool(r["extra"].get("traced")) is traced]
    contended = sorted(r.get("run_key", "?") for r in base if (r["extra"].get("pool_workers") or 1) > 1 or "level" in r["extra"])
    if contended:
        raise SystemExit(f"--baseline holds runs under contention (a pool or a curve level), which would inflate the baseline: {contended[:5]}")
    own, own_read = Cv.single_run_walls(base), Cv.single_read_phases(base)
    missing = sorted(f"{o}/{la}/{i}" for o, la in cells for i in instances if (o, la, i) not in own)
    if missing:
        raise SystemExit(f"no clean single run ({'traced' if traced else 'untraced'}) for {missing[:6]}: each cell is compared with its own")
    if hr is not None and (bad := Cv.check_scaled_references(own, own_read, hr, cells)):      # a ratio the loader takes can still scale a baseline out of range: refused before anything is written
        raise SystemExit(f"--host-reference-ratios {hr_path}: {bad[0]}" + (f" (and {len(bad) - 1} more)" if len(bad) > 1 else ""))
    per_run = args.mem_per_run_gib if args.mem_per_run_gib is not None else Cv.mem_per_run_gib(base)
    if per_run is None:
        raise SystemExit("a baseline run lacks a peak for one of its containers: pass --mem-per-run-gib, or use baselines that recorded peaks")
    site_g_hash = provider_state()
    out.mkdir(parents=True, exist_ok=True)
    hr_copy = out / Cv.HOST_RATIOS_COPY
    if hr_copy.exists():        # one set of host references per curve: refused before a manifest is written or a part started
        if hr is None:
            raise SystemExit(f"curve-multi: this --out was judged with host references ({hr_copy}): pass the same --host-reference-ratios file, or use a new --out")
        try:
            kept = hashlib.sha256(hr_copy.read_bytes()).hexdigest()
        except OSError as e:
            raise SystemExit(f"curve-multi: {hr_copy} cannot be read ({e}): whether this --out was judged with these host references is not known; use a new --out")
        if kept != hr["sha256"]:
            raise SystemExit(f"curve-multi: --host-reference-ratios {hr_path} differs from the file this --out was judged with ({hr_copy}): one set of host references "
                             f"per curve; pass the same file, or use a new --out")
    if args.resume and hr is not None and not hr_copy.exists() and _has_decisions(out / "curve_decisions.jsonl", args.block, args.rep):     # a start without --resume is refused by `_manifest` before it writes
        raise SystemExit(f"curve-multi: this --out was judged without host references, or its copy of the file ({hr_copy.name}) is gone: {out / 'curve_decisions.jsonl'} has decisions "
                         f"for block {args.block} rep {args.rep}, which were not made against {hr_path}; use a new --out (nothing is written)")
    state_file, prior = (check_sitting(out, args.block, args.rep, site_g_hash, decision, None if prof is None else prof["profile_id"]) if args.resume
                         else (out / f"multihost_state_block{args.block}_rep{args.rep}.json", None))
    if args.resume:
        reconcile_stale(out, hosts, lps, transport, kill=args.kill_stale)
    from . import bundle
    m = M._manifest(out, f"curve_multi_block{args.block}", resume=args.resume, seed=args.seed, block=args.block, levels=levels, capacity=caps,
                    split=args.split, hosts={n: {"remote": s.remote, "slot_keys": s.slot_keys} for n, s in hosts.specs.items()}, stop=args.stop, rep=args.rep,
                    baseline=args.baseline, instances=instances, traced=traced, mem_per_run_gib=per_run, site_g_settings_sha256=site_g_hash, runner=spec,
                    above_16_decision=decision, **({"duty_profile": str(args.duty_profile), "duty_profile_id": prof["profile_id"], "max_m_runs": prof["max_m_runs"]}
                                                      if prof is not None else {}),
                    **({"host_reference": Cv.host_reference_record(hr)} if hr is not None else {}))
    if (why := DC.baseline_image_problem(args.baseline, None if spec else m.get("image_id"))):
        raise SystemExit(why)
    if not state_file.exists():
        _write_json(state_file, {"site_g_settings_sha256": site_g_hash, "first_sitting_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "block": args.block, "rep": args.rep,
                                 **({"above_16_decision": decision} if decision else {}), **({"duty_profile_id": prof["profile_id"]} if prof is not None else {})})
    elif decision:                                       # a later sitting that first needs science's ruling: it is added, never replaced (check_sitting refused a different one)
        st = json.loads(state_file.read_text())
        if st.get("above_16_decision") != decision:
            _write_json(state_file, {**st, "above_16_decision": decision})
    refs: dict[str, str] = {}
    if not spec:
        from .reference import load_or_build_reference
        man, recs, truth = M._common(args)
        refs = load_or_build_reference(out, [recs[i] for i in instances])
    bid = Cv.baseline_id(own, own_read, hr)
    if prof is not None:
        bid = DC.composed_id(bid, prof["profile_id"])      # a resume under another profile is refused by the decisions too (curve.decided_levels)
    ctx = Ctx(args, M, out, hosts, caps, instances, cells, traced, own, own_read, bid, site_g_hash, per_run, refs, None if spec else m["image"],
              None if spec else m.get("image_id"), os.environ.get("ICSA_RUN_SHA"), spec, bundle.source_sha256(), m_shares=m_share_of, decision=decision, hard_max=hard_max,
              prof=prof, prof_blob=prof_blob, transport=transport, sleep=sleep, host_ratios=hr)
    try:
        history = _level_lines(out / "curve_decisions.jsonl", args.block, args.rep, traced, bid)
    except ValueError as e:
        raise SystemExit(f"curve block {args.block}: {e}; use a new --out")
    if hr is not None and not hr_copy.exists():     # kept only now, after every refusal above: a refused resume leaves no copy that would refuse the out's later resumes. The report reads this copy
        data = Path(hr["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != hr["sha256"]:
            raise SystemExit(f"curve-multi: --host-reference-ratios {hr_path} changed after it was read: the curve is judged by the bytes it was loaded from; nothing is run")
        hr_copy.write_bytes(data)
    stopped: dict[str, Any] = {}

    def measured(level: int, rerun: dict | None) -> dict:
        """One attempt at the level, its line written and kept in `history`; an infrastructure line stops the search (a resume tries the same attempt again)."""
        rec = run_level(ctx, level, rerun)
        Cv.append_decision(out / "curve_decisions.jsonl", rec)
        history.setdefault(level, []).append(rec)
        print(json.dumps(rec), flush=True)
        if rec.get("infrastructure"):
            stopped.update(level=level, kind=rec["infrastructure"], detail=rec["detail"])
            raise _Stop()
        return rec

    def passes(level: int) -> bool:
        kind, first = level_state(history.get(level, []), lambda line: rerun_blocker(ctx, line) is None)
        if kind == "decided":
            print(f"level {level}: already decided ({'pass' if first else 'fail'}) in curve_decisions.jsonl, not re-run", flush=True)
            return first
        if kind == "open":
            first = measured(level, None)
            if first["passed"]:
                return True
            if first.get("failed_on") != "m_bound":
                return False
            why = rerun_blocker(ctx, first)
            if why is not None:
                print(f"level {level}: failed on M's bound, and is not rerun: {why}", flush=True)
                return False
        print(f"level {level}: failed on M's bound on one host; the one rerun, split across both hosts where it has all the M users", flush=True)
        return measured(level, first)["passed"]

    try:
        if sequence:
            results, state = Cv.run_sequence(levels, climb, floor, passes)
        else:
            results = Cv.search(levels, args.stop, passes)
    except _Stop:
        raise SystemExit(f"curve block {args.block}: level {stopped['level']} could not be run to a decision ({stopped['kind']}: {stopped['detail']}): "
                         f"an infrastructure failure of the level, recorded as such, never a pass; no cap is written; fix it and --resume")
    result = state["cap"] if sequence else Cv.cap_of(results)
    tail = {"block": args.block, "cap": result, "tried": [lv for lv, _ in results], "max_level": max_level, "cap_is_max_level": result == max_level,
            "rerun_levels": sorted(lv for lv, lines in history.items() if any(r.get("rerun_of") and not r.get("infrastructure") for r in lines)),
            "reason": ("every level down the ladder failed: no cap" if sequence else "the first level failed: no cap") if result is None else "last passing level",
            "capacity": caps, "site_g_settings_sha256": site_g_hash}
    if prof is not None:        # what the lines say of the cap, beside the driver's own: whether M's bound set it, and that the two readings agree
        try:
            rd = DC.cap_from_decisions(out / "curve_decisions.jsonl", args.block, args.rep, traced=traced, profile=prof)
            tail.update(cap_bound_by=rd["cap_bound_by"], m_bound=rd["cap_bound_by"] == "m_bound", capped_by_level=rd["capped_by_level"], cap_read_from_lines=rd["cap"],
                        cap_read_agrees=rd["cap"] == result, cap_final=rd["final"])
        except DC.DutyInputError as e:
            tail["cap_read_error"] = str(e)
    (out / f"curve_cap_block{args.block}.json").write_text(json.dumps(tail, indent=1))
    print(json.dumps(tail), flush=True)
    if result is None:
        raise SystemExit(f"curve block {args.block}: level {results[0][0]} failed the rule: NO CAP (nothing is applied)")


class _Stop(Exception):
    pass
