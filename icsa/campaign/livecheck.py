"""The live check (protocol amendment 25(e)): the pilot's, the calibration's and the main block's guard against a burst the duty-cycle curve could not show.

    "During the pilot, calibration and the main block, a fixed scripted read in T's and in M's S1 shape, about a minute each, runs every 30 minutes under the real
    load. If two consecutive probes of either shape exceed 1.25x their single-run time, dispatch lowers the total level by one step for all options together,
    recorded with its time. It rises again only on the science agent's word."
    (Replaced by amendment 29(f): the rise is by rule, below. No file, no word.)

What is here is the judgement, kept apart from the scheduler so that it can be tested without one (the scheduler's `_live_check_once` runs it):
- `run_probe`: one configured command (`python -m icsa.scripted live-probe`), its result checked and normalised. A command that fails, times out, prints no JSON
  line or numbers that do not agree, or whose probe says unknown, is `unknown`: neither a pass nor a breach. A ratio of exactly the limit is not a breach.
- `LiveState`: per shape, the streak of consecutive breaches (`unknown` neither extends nor resets it) and the run of unknowns; the steps taken; the probe history.
  It is the meta value `live_check` of the campaign store, written on every change and read back at `open()`: a restart keeps the lowered level.
- `lowered_cap`: the one rule that makes a step bind. With no step taken a cap is returned as configured; with `steps` taken, the highest level of the ladder at
  most the cap, `steps` places down the ladder, never below its lowest. A cap that is None (no cap configured for that block) stays None: there is no level to lower,
  and the status says which blocks that leaves unbound.

The level setting (science's rulings of 3 Nov, 00:28-00:31Z, and amendment 29(f)): the level in force is each configured cap lowered by `steps` places on `level_ladder`, for every cap
together, and `steps` is one value in the store (meta `live_check`), changed only by `lower_one` (a launch's start step, the live check, a command run from a shell:
`python -m icsa.campaign level-down`) and `raise_one` (the rise rule below, one step per rise). Each change is an entry of `changes` and an event `level_changed`, with who and why.
The dispatcher re-reads the value, so a change made from a shell binds without a restart.

THE RISE (29(f), replacing the science agent's word of 25(e) for every rise): "at the first check after 2 h [since the last change of level] with every live probe within 1.25x, no
provider 5xx or timeouts in the gate and sidecar logs, and op_worker's resident memory up by under 5% over those 2 h". `rise_decision` is that rule as a pure function of the three
inputs over the last 2 h. Not known is not a pass: no probe of a shape in the window, an unknown probe, a memory reading that does not cover the window, or a gate count missing from an
attempt that ended in it, all hold the level, and the decision says which. An empty window (no attempt ended in it) reads the error input as nothing seen and says so: the rise then rests on the
probes and the memory alone. What the error input can see is only what a record holds (`attempt_errors`): the gate's 5xx and resets of the attempts that ended in the window, on both hosts.
It cannot see a run in flight, a timeout (no record counts one) or the sidecar's 5xx (the sidecar summary has no such class); the decision records those as not measured, never as zero.

Why the probe is not "about a minute" here: the scripted S1 cell reads every required daily file of an instance, 1,544 of them (1,452 baseline days and 92 target
days), one after the other. At the per-file times measured on 1 Nov (T 0.41 s with the fixed gate, results/scripted/gate_ab2.jsonl; M 0.25 s, results/m-throughput/NOTES.md)
that is about 630 s for T and 390 to 520 s for M, and the single-run baselines will say what they really are (the probe prints `single_s`). So the probes are minutes,
and what each adds to the provider is a whole S1 cell, one reader, for that long every 30 minutes: about 23 to 31 % of one sandbox's duty for M and 37 % for T (sandbox
start and teardown included, about 30 s each), not the 3.3 % of a one-minute read.
Trimming the cell to a minute (a subset of its days) would be a different probe, with a baseline of its own, and is not done here: it is science's to decide.
"""
from __future__ import annotations

import dataclasses
import json
import math
import statistics
import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence

Event = tuple[str, str | None, str]

SHAPES = ("T", "M")
CONSECUTIVE = 2                  # amendment 25(e): two consecutive probes of either shape
HISTORY_KEEP = 400               # probes kept in the store's meta value (two a period)
TOKEN_SOURCE = "icsa.scripted.slot_tokens:factory"     # the probe leases its slot user: never the admin token
META = "live_check"
RISE_AFTER_S = 7200.0            # 29(f): 2 h since the last change of level
RISE_MEM_MAX_PCT = 5.0           # 29(f): op_worker's resident memory up by under 5% over the window
RISE_WHO = "rule 29(f)"
STOP_GRACE_S = 300.0             # a probe asked to end with the campaign: SIGTERM, then this long for its sandbox (an M teardown is several bounded commands: icsa/sandbox/teardown.py) to be stopped, then SIGKILL
RATIO_AGREES = 0.01              # the printed ratio must be read_s / single_s within this fraction


def max_steps(ladder: Sequence[int]) -> int:
    return max(0, len(ladder) - 1)


def lowered_cap(cap: int | None, ladder: Sequence[int], steps: int) -> int | None:
    """The cap in force after `steps` lowerings. None and zero steps are returned as they are."""
    if steps <= 0 or cap is None:
        return cap
    if not ladder:
        raise ValueError(f"{steps} lowering step(s) are recorded but the launch has no level_ladder: the lowered level cannot be computed")
    below = [x for x in ladder if x <= cap]
    if not below:                          # already under the ladder's lowest: nothing on the ladder to step down to
        return cap
    return ladder[max(0, list(ladder).index(below[-1]) - steps)]


def group_caps(cfg: Any) -> dict[str, int | None]:
    """The configured caps by name: each block of `max_sandboxes_by_block`, and "global" (`max_sandboxes`, the blocks without an entry)."""
    return {**dict(cfg.max_sandboxes_by_block), "global": cfg.max_sandboxes}


def effective_caps(cfg: Any, steps: int) -> dict[str, dict[str, int | None]]:
    return {g: {"configured": c, "effective": lowered_cap(c, cfg.level_ladder, steps)} for g, c in group_caps(cfg).items()}


def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def ladder_problems(cfg: Any) -> list[str]:
    """The level setting's own: the ladder (the frozen levels) and the start steps. Checked when the check is on or a start step is asked for."""
    p: list[str] = []
    lad = cfg.level_ladder
    if not isinstance(lad, list) or len(lad) < 2 or not all(isinstance(x, int) and not isinstance(x, bool) and x >= 1 for x in lad) \
            or any(b <= a for a, b in zip(lad, lad[1:])):
        p.append("level_ladder must be the frozen levels, whole numbers of at least 1, strictly ascending, at least two (one step to take)")
    elif not isinstance(cfg.level_start_steps, int) or isinstance(cfg.level_start_steps, bool) or not 0 <= cfg.level_start_steps <= max_steps(lad):
        p.append(f"level_start_steps must be a whole number from 0 to {max_steps(lad)} (the ladder's steps)")
    return p


def config_problems(cfg: Any) -> list[str]:
    """Every problem of the live check's settings, named at once. Only a launch that gives commands is checked for the probes (no commands: the check is off); the ladder is also
    checked for a launch that asks for start steps."""
    cmds = cfg.live_check_cmds
    if not cmds:
        return ladder_problems(cfg) if getattr(cfg, "level_start_steps", 0) else []
    p: list[str] = []
    if not isinstance(cmds, dict) or set(cmds) != set(SHAPES):
        p.append(f"live_check_cmds must name exactly the shapes {list(SHAPES)}: a guard that sees only one of them is half blind")
    else:
        for s, c in cmds.items():
            if not isinstance(c, list) or not c or not all(isinstance(a, str) and a for a in c):
                p.append(f"live_check_cmds[{s!r}] must be a non-empty list of non-empty strings")
    pf = getattr(cfg, "live_check_probe_files", None)
    if pf is not None:
        if not isinstance(pf, dict) or not set(pf) <= set(SHAPES):
            p.append(f"live_check_probe_files must be an object over the shapes {list(SHAPES)} (a whole number of files, or null for the whole cell)")
        else:
            for s, n in pf.items():
                if n is not None and (isinstance(n, bool) or not isinstance(n, int) or n < 1):
                    p.append(f"live_check_probe_files[{s!r}] must be a whole number of at least 1, or null for the whole cell")
                if n is not None and isinstance(cmds, dict) and isinstance(cmds.get(s), list) and any(isinstance(a, str) and a.split("=")[0] == "--probe-files" for a in cmds[s]):
                    p.append(f"live_check_cmds[{s!r}] already carries --probe-files: give the count in live_check_probe_files alone")
    keys = cfg.live_check_slot_keys
    if not isinstance(keys, dict) or set(keys) != set(SHAPES) or not all(isinstance(v, str) and v for v in keys.values()):
        p.append(f"live_check_slot_keys must give one slot key for each of {list(SHAPES)}, the probe's own slot users")
    elif len(set(keys.values())) != len(keys):
        p.append("live_check_slot_keys: the two shapes need two different slot users")
    p += ladder_problems(cfg)
    if not _num(cfg.live_check_every_s) or cfg.live_check_every_s <= 0:
        p.append("live_check_every_s must be above zero")
    if not _num(cfg.live_check_limit) or cfg.live_check_limit <= 1.0:
        p.append("live_check_limit must be above 1 (the registered 1.25)")
    if not _num(cfg.live_check_timeout_s) or cfg.live_check_timeout_s <= 0:
        p.append("live_check_timeout_s must be above zero")
    if not _num(cfg.level_rise_after_s) or cfg.level_rise_after_s <= 0:
        p.append("level_rise_after_s must be above zero (29(f): 7200)")
    return p


def probe_files_problem(cfg: Any) -> str | None:
    """Amendment 30(b): the live probe is "a fixed subset in a fixed order, about 150 files for T and 240 for M, about a minute". A real launch (the caller's test) whose commands
    are given must say how many files each shape reads, in `live_check_probe_files`: with none the probe reads the whole cell, some ten minutes every period. A count carried by a
    command's argv alone is none: the judge compares each line's `probe_files` with this setting, so every probe would read UNKNOWN. None when every shape has its count."""
    pf = cfg.live_check_probe_files if isinstance(cfg.live_check_probe_files, dict) else {}
    lacking = [s for s in SHAPES if pf.get(s) is None]
    if not lacking:
        return None
    cmds = cfg.live_check_cmds if isinstance(cfg.live_check_cmds, dict) else {}
    in_argv = [s for s in lacking if any(t.split("=")[0] == "--probe-files" for a in (cmds.get(s) or []) for t in str(a).split())]
    return (f"live_check_probe_files gives no count of files for {', '.join(lacking)}: amendment 30(b) makes the probe a fixed subset (about 150 files for T and 240 for M), "
            "and with no count it reads the whole cell of 1,544 files, some ten minutes"
            + (f" (a count in the argv of {', '.join(in_argv)} alone does not do: the judge compares each probe line's probe_files with this setting, so every probe would read UNKNOWN)" if in_argv else "")
            + ". Give a whole number for each shape, or set live_check_required false, which the event log says")


# ---- one probe ------------------------------------------------------------------------------------------------------------
def unknown(shape: str, why: str, **kw: Any) -> dict[str, Any]:
    return {"shape": shape, "state": "unknown", "read_s": kw.get("read_s"), "single_s": kw.get("single_s"), "ratio": None, "breach": None,
            "why": why[:400], "run_key": kw.get("run_key")}


def probe_argv(cmd: Sequence[str], files: Any) -> list[str]:
    """The probe's command with the launch's count of files for its shape (`live_check_probe_files[shape]`): `--probe-files n` after the argv; none, the argv as it is."""
    return list(cmd) + ([] if files is None else ["--probe-files", str(files)])


def judge(shape: str, d: Any, limit: float, files: Any = None) -> dict[str, Any]:
    """A probe's printed line, checked. The ratio is computed here from the read time and the single-run time, and the printed one must agree. `files` is the count the launch
    asked for: a line that carries another (or none, or one when none was asked) read a different cell, so it is unknown, never a pass or a breach."""
    if not isinstance(d, dict) or d.get("shape") != shape:
        return unknown(shape, f"the probe printed no line for shape {shape}")
    rk = d.get("run_key") if isinstance(d.get("run_key"), str) else None
    if d.get("probe_files") != files or isinstance(d.get("probe_files"), bool):
        return unknown(shape, f"the probe's line carries probe_files {d.get('probe_files')!r}, not the {files!r} the launch asked for: it read another cell", run_key=rk)
    if d.get("state") != "ok":
        return unknown(shape, str(d.get("why") or "the probe says unknown"), run_key=rk)
    rs, ss, ra = d.get("read_s"), d.get("single_s"), d.get("ratio")
    if not (_num(rs) and _num(ss) and _num(ra)) or rs < 0 or ss <= 0:
        return unknown(shape, "the probe says ok but its read time, single-run time or ratio is not a usable number", run_key=rk)
    ratio = rs / ss
    if abs(ratio - ra) > RATIO_AGREES * max(ratio, ra, 1e-9):
        return unknown(shape, f"the probe's ratio {ra} is not its read time over its single-run time ({ratio:.4f})", read_s=rs, single_s=ss, run_key=rk)
    return {"shape": shape, "state": "ok", "read_s": float(rs), "single_s": float(ss), "ratio": ratio, "breach": ratio > limit,
            "why": str(d.get("why") or "")[:400], "run_key": rk}


def run_probe(shape: str, cmd: Sequence[str], env: dict[str, str], timeout_s: float, limit: float, run: Callable = subprocess.run, files: Any = None) -> dict[str, Any]:
    """Run one probe command (with `--probe-files files` when the launch gives a count: `probe_argv`) and judge its output. Nothing here raises: a probe that could not be had is `unknown`."""
    try:
        p = run(probe_argv(cmd, files), capture_output=True, text=True, timeout=timeout_s, env=env)
    except subprocess.TimeoutExpired:
        return unknown(shape, f"the probe timed out after {timeout_s:g} s (it was asked to end; if it had to be killed its sandbox may be left: look at the host)")
    except (OSError, subprocess.SubprocessError) as e:
        return unknown(shape, f"the probe could not run: {type(e).__name__}")
    if p.returncode != 0:
        tail = " ".join((p.stderr or "").split())[-200:]
        return unknown(shape, f"the probe exited {p.returncode}" + (f": {tail}" if tail else ""))
    lines = [x for x in (p.stdout or "").splitlines() if x.strip().startswith("{")]
    try:
        d = json.loads(lines[-1])
    except (IndexError, ValueError):
        return unknown(shape, "the probe printed no JSON line")
    return judge(shape, d, limit, files)


# ---- the state ------------------------------------------------------------------------------------------------------------
@dataclasses.dataclass
class LiveState:
    steps: int = 0                                    # the level in force: steps below the configured caps (a raise subtracts)
    streak: dict[str, int] = dataclasses.field(default_factory=lambda: {s: 0 for s in SHAPES})
    streak_ratios: dict[str, list[float]] = dataclasses.field(default_factory=lambda: {s: [] for s in SHAPES})
    unknown_run: dict[str, int] = dataclasses.field(default_factory=lambda: {s: 0 for s in SHAPES})
    last: dict[str, dict] = dataclasses.field(default_factory=dict)
    history: list[dict] = dataclasses.field(default_factory=list)
    probes: int = 0
    skips: int = 0
    last_skip: dict | None = None
    lowered_utc: str | None = None                    # the latest lowering, of any kind
    changes: list[dict] = dataclasses.field(default_factory=list)       # every change of the level, in order: utc, kind (start|live_check|command|rule), direction, steps, who, why, caps
    rise: dict | None = None                          # the latest check of the rise rule that was not a plain wait: state (hold|unknown|rise), why, utc, inputs

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, text: str | None) -> "LiveState":
        """No record = a fresh state. A record that cannot be read is an error: the steps taken are the lowered level, and 'none' would silently restore it."""
        if text is None:
            return cls()
        try:
            d = json.loads(text)
            st = cls(**d)
            ok = (isinstance(st.steps, int) and not isinstance(st.steps, bool) and st.steps >= 0 and set(st.streak) == set(SHAPES)
                  and set(st.unknown_run) == set(SHAPES) and all(isinstance(v, int) and v >= 0 for v in (*st.streak.values(), *st.unknown_run.values())))
        except (ValueError, TypeError):
            ok = False
        if not ok:
            raise ValueError("the stored live-check state (meta live_check) cannot be read: the steps taken, which are the lowered level, are unknown")
        return st

    def observe(self, shape: str, probe: dict, now: str) -> str:
        """Fold one probe in. Returns "breach", "pass" or "unknown". `unknown` neither extends nor resets a streak."""
        kind = "unknown" if probe["state"] != "ok" else ("breach" if probe["breach"] else "pass")
        self.probes += 1
        entry = {"utc": now, "shape": shape, "kind": kind, "ratio": probe["ratio"], "read_s": probe["read_s"], "single_s": probe["single_s"],
                 "why": probe["why"], "run_key": probe["run_key"]}
        self.last[shape] = entry
        self.history = (self.history + [entry])[-HISTORY_KEEP:]
        if kind == "breach":
            self.streak[shape] += 1
            self.streak_ratios[shape] = self.streak_ratios[shape] + [round(probe["ratio"], 4)]
            self.unknown_run[shape] = 0
        elif kind == "pass":
            self.streak[shape], self.streak_ratios[shape], self.unknown_run[shape] = 0, [], 0
        else:
            self.unknown_run[shape] += 1
        return kind

    def due(self, shape: str) -> bool:
        return self.streak[shape] >= CONSECUTIVE


# ---- the level: every change of it, here and nowhere else -------------------------------------------------------------------------
def _caps_in_force(cfg: Any, steps: int) -> dict[str, int | None]:
    return {g: c["effective"] for g, c in effective_caps(cfg, steps).items()}


def lower_one(st: LiveState, cfg: Any, kind: str, who: str, why: str, now: str) -> tuple[bool, list[Event]]:
    """One step down for every cap together. `kind`: start (the launch's setting), live_check (two probes over the limit), command (a person or the restart command, from a shell).
    At the ladder's lowest nothing changes and the event says so. Returns (lowered, the events to write with the new state)."""
    top = max_steps(cfg.level_ladder)
    if st.steps >= top:
        return False, [("level_at_floor", None, f"{kind} by {who} asked for one step down ({why}), but the level is already at the ladder's lowest ({cfg.level_ladder[0]}, step {st.steps} of {top}): nothing to lower")]
    before = st.steps
    st.steps += 1
    st.lowered_utc = now
    st.rise = None                                     # the clock of the rise restarts, and what it held is stale
    caps = _caps_in_force(cfg, st.steps)
    st.changes.append({"utc": now, "kind": kind, "direction": "lower", "steps_before": before, "steps": st.steps, "who": who, "why": why, "caps": caps})
    return True, [("level_changed", None, f"LOWERED by {who} ({kind}) at {now}: step {before} -> {st.steps} of {top}, for every cap and all options together; why: {why}; caps now {caps} "
                                          f"(ladder {list(cfg.level_ladder)}); runs in flight are not stopped; it rises only by rule 29(f): 2 h with every probe within the limit, no 5xx or timeouts, op_worker memory under +5%")]


def raise_one(st: LiveState, cfg: Any, why: str, now: str, inputs: dict) -> tuple[bool, list[Event]]:
    """One step up, by rule 29(f) and nothing else (`rise_decision` said rise; the only caller is the dispatcher's rise check). The change names the inputs the rule read. With
    nothing lowered it changes nothing."""
    if st.steps <= 0:
        return False, []
    before = st.steps
    st.steps -= 1
    st.streak, st.streak_ratios = {s: 0 for s in SHAPES}, {s: [] for s in SHAPES}      # readings taken at the lower level are not this level's
    st.rise = None
    caps = _caps_in_force(cfg, st.steps)
    st.changes.append({"utc": now, "kind": "rule", "direction": "raise", "steps_before": before, "steps": st.steps, "who": RISE_WHO, "why": why, "inputs": inputs, "caps": caps})
    return True, [("level_changed", None, f"RAISED by {RISE_WHO} at {now}: step {before} -> {st.steps}; why: {why}; inputs read: {json.dumps(inputs, sort_keys=True)}; caps now {caps}; "
                                          f"{st.steps} step(s) still below the configured caps")]


def start_level(st: LiveState, cfg: Any, now: str) -> list[Event]:
    """The launch's `level_start_steps`: at least that many steps down (a real main launch asks for 1: main starts one level below the curve's cap). It only lowers: a level already
    lower stays, and no launch setting raises."""
    want = int(getattr(cfg, "level_start_steps", 0) or 0)
    if want <= st.steps:
        return []
    before = st.steps
    st.steps = want
    st.lowered_utc = now
    st.rise = None
    caps = _caps_in_force(cfg, st.steps)
    why = f"level_start_steps {want}: main starts below the curve's cap and rises by rule 29(f)"
    st.changes.append({"utc": now, "kind": "start", "direction": "lower", "steps_before": before, "steps": want, "who": "launch config", "why": why, "caps": caps})
    return [("level_changed", None, f"LOWERED by launch config (start) at {now}: step {before} -> {want} of {max_steps(cfg.level_ladder)}; why: {why}; caps now {caps}")]


def record_probe(st: LiveState, cfg: Any, shape: str, probe: dict, now: str, lowered_now: bool, waited_s: float = 0.0) -> tuple[bool, list[Event]]:
    """Fold a probe into the state. Returns (this probe lowered the level, the events). One step at most per round: a second shape that reaches its streak in the same round
    resets and says it was covered."""
    kind = st.observe(shape, probe, now)
    st.last_skip = None
    said = f"UNKNOWN: {probe['why']}" if kind == "unknown" else f"{'above' if kind == 'breach' else 'within'} the limit: {probe['ratio']:.3f}x"
    events: list[Event] = [("live_check_probe", None, f"{shape}: {said} (read {probe['read_s']} s against {probe['single_s']} s alone; limit {cfg.live_check_limit:g}); "
                                                      f"streak {st.streak[shape]} of {CONSECUTIVE}; waited {waited_s:.0f} s for a place; {probe['run_key']}")]
    lowered = False
    if st.due(shape):
        ratios = st.streak_ratios[shape]
        st.streak[shape], st.streak_ratios[shape] = 0, []
        if lowered_now:
            events.append(("live_check_covered", None, f"{shape}: {CONSECUTIVE} consecutive probes above the limit ({ratios}) in the round that already lowered the level: no second step"))
        else:
            lowered, ev = lower_one(st, cfg, "live_check", "live check",
                                    f"{shape}: {CONSECUTIVE} consecutive probes above {cfg.live_check_limit:g}x their single-run read time ({ratios})", now)
            events += ev
    return lowered, events


# ---- the rise rule's inputs and the rule ------------------------------------------------------------------------------------------
def _epoch(v: Any) -> float | None:
    """A time as epoch seconds: a number, or an ISO string. Anything else is None."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    if isinstance(v, str):
        import datetime as dt
        try:
            return dt.datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _dig(d: Any, path: str) -> Any:
    for k in path.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def read_memory(path: str | Path, field: str, time_field: str, id_field: str, t0: float, t1: float, gap_s: float, max_bytes: int = 8 << 20) -> tuple[dict | None, str]:
    """op_worker's resident memory over [t0, t1] (epoch s) from lane-mon's provider_mon jsonl (one JSON sample per line; `field` and `time_field` are dotted paths in it; a value that
    could not be read is null there and is skipped here). Known only if the first reading is within `gap_s` after t0 and the last within `gap_s` before t1, so a gap in the monitor
    cannot read as flat; and if `id_field` (op_worker's process id) is present and changed inside the window, the memory is not comparable (a restart). Returns (reading, "") or (None, why)."""
    if not path:
        return None, "no level_memory_file in the launch config: op_worker's memory is not read"
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            raw = f.read().decode("utf-8", "replace")
    except OSError as e:
        return None, f"the memory file {path} cannot be read ({type(e).__name__})"
    pts: list[tuple[float, float, Any]] = []
    for ln in raw.splitlines():
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("kind", "sample") != "sample":
            continue
        t, v = _epoch(_dig(d, time_field)), _dig(d, field)
        if t is None or not _num(v) or not (t0 <= t <= t1):
            continue
        pts.append((t, float(v), _dig(d, id_field) if id_field else None))
    if not pts:
        return None, f"no reading of {field} between the window's ends in {path}"
    pts.sort(key=lambda x: x[0])
    first, last = pts[0], pts[-1]
    if first[0] - t0 > gap_s or t1 - last[0] > gap_s:
        return None, f"the readings of {field} do not cover the window (first {first[0] - t0:.0f} s after its start, last {t1 - last[0]:.0f} s before its end; allowed {gap_s:g} s)"
    ids = {p[2] for p in pts if p[2] is not None}
    if len(ids) > 1:
        return None, f"op_worker's process id changed inside the window ({sorted(map(str, ids))[:3]}): a restart, the memory is not comparable"
    k = max(1, min(5, len(pts) // 2))          # the medians of the first and of the last readings (up to five each), as lane-mon's growth figure is formed: one spike does not decide
    a, b = statistics.median(p[1] for p in pts[:k]), statistics.median(p[1] for p in pts[-k:])
    if a <= 0:
        return None, f"the first reading of {field} is {a:g}: no percentage can be formed"
    return {"field": field, "start": a, "end": b, "pct": round((b - a) / a * 100.0, 3), "readings": len(pts), "median_of": k}, ""


GATE_OPTIONS = ("T", "T-unpaginated", "D")


def attempt_errors(store: Any, t0: float, t1: float, cache: dict | None = None) -> tuple[dict | None, str]:
    """The provider errors the records hold for the attempts that ENDED in [t0, t1] (epoch s), on both hosts (an attempt on the other host is in the dispatcher's own run dir once
    it ended and was pulled): the gate's 5xx and resets (sandbox.gate_transfers.errors: gate_5xx, upstream_5xx, gate_resets, upstream_resets) of the T, T-unpaginated and D attempts.
    Not read, and said so: a run in flight (its logs are read at its teardown), timeouts (no record counts them), M's sidecar (its summary has no 5xx or timeout class). A gate-option
    attempt with no count (no record, an unreadable one, an unavailable gate log) makes the reading unknown. No attempt ended: nothing seen, and the note says the probes decide alone."""
    cache = cache if cache is not None else {}
    rows = store.q("SELECT a.id, a.run_key, a.state, a.ended_utc, a.run_dir, a.infra_kind, r.option FROM attempts a JOIN runs r ON r.run_key = a.run_key "
                   "WHERE a.ended_utc IS NOT NULL AND a.state != 'running' AND a.ended_utc >= ?", (_iso_floor(t0),))
    seen, missing, errors, gate_read, m_n, from_log, left_out = 0, [], 0, 0, 0, 0, 0
    for r in rows:
        t = _epoch(r["ended_utc"])
        if t is None or not (t0 <= t <= t1):
            continue
        seen += 1
        gate_opt = r["option"] in GATE_OPTIONS
        if gate_opt:
            got = cache.get(r["id"])
            if got is None:
                got = cache[r["id"]] = _gate_count(r["run_dir"])
        else:
            got = 0 if _has_record(r["run_dir"]) else None      # amendment 30(a), in any option: the sidecar is not measured, but no record is no reading
        if got is None and r["infra_kind"] == "endpoint":
            # Science, #34, 4 Nov 02:46Z, every option alike: a model endpoint's failure leaves no record. One that never started a sandbox read nothing from site_g and is
            # left out; one whose collected gate log ends in its close lines is counted from that log by the sandbox's own summary. Anything else stays unknown.
            if not _sandbox_started(r["run_dir"]):
                left_out += 1
                seen -= 1
                continue
            key = ("gate_log", r["id"])                      # a failed attempt's log is final: read it once
            if key not in cache:
                cache[key] = _gate_log_count(r["run_dir"])
            got = cache[key]
            if got is not None:
                from_log += 1
                if gate_opt:
                    gate_read += 1
                    errors += got
                else:
                    m_n += 1                                    # M counts 0, as a normal M record does (30(a); science, #34, 4 Nov 03:07Z): its errors are not measured
                continue
        if got is None:
            missing.append(f"{r['run_key']} (attempt {r['id']})")
        elif gate_opt:
            gate_read += 1
            errors += got
        else:
            m_n += 1
    note = ("not measured: timeouts (no record counts them), M's sidecar (no 5xx or timeout class), runs in flight")
    counts = f"from_gate_log {from_log}, left_out {left_out}"
    if missing:
        return None, (f"{len(missing)} of the {seen} attempt(s) that ended in the window have no record or no gate count in it "
                      f"({', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}); {counts}")
    out = {"attempts_ended": seen, "gate_attempts_read": gate_read, "sidecar_attempts": m_n, "gate_5xx_and_resets": errors, "from_gate_log": from_log,
           "left_out": left_out, "not_measured": note}
    if seen == 0:
        out["note"] = "no attempt ended in the window: the rise rests on the probes and the memory alone"
    return out, ""


def _iso_floor(t0: float) -> str:
    import datetime as dt
    return (dt.datetime.fromtimestamp(t0, dt.timezone.utc) - dt.timedelta(minutes=1)).isoformat()


SANDBOX_ARTIFACTS = ("gate_requests.jsonl", "cells", "trace", "output", "reaped")    # what a run dir holds once its sandbox has run (collected, or reaped from a dead one)


def _sandbox_started(run_dir: Any) -> bool:
    """Did this attempt's sandbox start? True if its run dir holds anything a sandbox leaves (a gate log, cells, a trace, output, a reaped copy), and when the run dir
    cannot be read (never left out on a doubt)."""
    if not run_dir:
        return True
    try:
        d = Path(run_dir)
        if not d.is_dir():
            return True
        return any((d / x).exists() for x in SANDBOX_ARTIFACTS)
    except OSError:
        return True


def _gate_log_count(run_dir: Any) -> int | None:
    """gate_5xx + gate_resets + upstream_5xx + upstream_resets from an attempt's collected gate log by the sandbox's own summary (`summarize_gate_log`), when the log ends
    in its close lines (its last line a `conn_close`: the gate wrote its connections' ends, at its teardown or as they came). None otherwise: no log, an unreadable or torn
    one, or one that stops on a request line (the gate may have stopped mid-run, so the log may hold less than happened)."""
    if not run_dir:
        return None
    try:
        lines = [x for x in (Path(run_dir) / "gate_requests.jsonl").read_text().splitlines() if x.strip()]
        if not lines or json.loads(lines[-1]).get("event") != "conn_close":
            return None
        from icsa.sandbox.sandbox import summarize_gate_log
        errs = summarize_gate_log(lines)["errors"]
        vals = [errs.get(k) for k in ("gate_5xx", "gate_resets", "upstream_5xx", "upstream_resets")]
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
            return None
        return sum(vals)
    except (OSError, ValueError, AttributeError, TypeError, KeyError):
        return None


def _has_record(run_dir: Any) -> bool:
    """An attempt's run_record.json is there and reads as a record."""
    if not run_dir:
        return False
    try:
        return isinstance(json.loads((Path(run_dir) / "run_record.json").read_text()), dict)
    except (OSError, ValueError):
        return False


def _gate_count(run_dir: Any) -> int | None:
    """gate_5xx + gate_resets + upstream_5xx + upstream_resets of one attempt's record, or None when it is not there or says unavailable. Never 0 for a record that cannot say."""
    if not run_dir:
        return None
    try:
        rec = json.loads((Path(run_dir) / "run_record.json").read_text())
        errs = ((rec.get("sandbox") or {}).get("gate_transfers") or {}).get("errors")
        if not isinstance(errs, dict):
            return None
        vals = [errs.get(k) for k in ("gate_5xx", "gate_resets", "upstream_5xx", "upstream_resets")]
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
            return None
        return sum(vals)
    except (OSError, ValueError, AttributeError):
        return None


def probes_in_window(history: list[dict], t0: float, t1: float) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {s: [] for s in SHAPES}
    for h in history:
        t = _epoch(h.get("utc"))
        if t is not None and t0 <= t <= t1 and h.get("shape") in out:
            out[h["shape"]].append(h)
    return out


def rise_decision(*, now: float, since: float, history: list[dict], limit: float, memory: tuple[dict | None, str], errors: tuple[dict | None, str],
                  window_s: float = RISE_AFTER_S, mem_max_pct: float = RISE_MEM_MAX_PCT) -> dict:
    """Amendment 29(f) as a function of its three inputs over the last `window_s` (default 2 h) and of `since`, the time of the last change of level (the clock restarts at every
    change). state: "waiting" (the window since the last change is not over), "rise", "hold" (an input is known and fails), "unknown" (no failure seen, but an input is not known: no rise).
    `why` names what failed or is missing; `inputs` is what was read."""
    elapsed = now - since
    if elapsed < window_s:
        return {"state": "waiting", "why": f"{(window_s - elapsed) / 60:.0f} min until {window_s / 3600:g} h have passed since the last change of level", "inputs": {}}
    t0 = now - window_s
    holds: list[str] = []
    unknowns: list[str] = []
    pr = probes_in_window(history, t0, now)
    pin: dict[str, Any] = {}
    for s in SHAPES:
        hs = pr[s]
        ratios = [h["ratio"] for h in hs if h.get("kind") in ("pass", "breach") and isinstance(h.get("ratio"), (int, float))]
        pin[s] = {"probes": len(hs), "unknown": sum(h.get("kind") == "unknown" for h in hs), "max_ratio": round(max(ratios), 4) if ratios else None}
        if not hs:
            unknowns.append(f"no {s} probe in the window")
        if pin[s]["unknown"]:
            unknowns.append(f"{pin[s]['unknown']} {s} probe(s) in the window UNKNOWN")
        over = [h for h in hs if h.get("kind") == "breach"]
        if over:
            holds.append(f"{len(over)} {s} probe(s) in the window above {limit:g}x (max {max(h['ratio'] for h in over):.2f}x)")
    mem, mwhy = memory
    if mem is None:
        unknowns.append(mwhy)
    elif mem["pct"] >= mem_max_pct:
        holds.append(f"op_worker memory up {mem['pct']:.2f}% over the window (limit under {mem_max_pct:g}%)")
    err, ewhy = errors
    if err is None:
        unknowns.append(ewhy)
    elif err.get("gate_5xx_and_resets"):
        holds.append(f"{err['gate_5xx_and_resets']} gate 5xx or reset(s) in the {err['attempts_ended']} attempt(s) that ended in the window")
    inputs = {"window_s": window_s, "since_s_ago": round(elapsed), "probes": pin, "memory": mem or {"unknown": mwhy}, "errors": err or {"unknown": ewhy}}
    if holds:
        return {"state": "hold", "why": "; ".join(holds + (["also not known: " + "; ".join(unknowns)] if unknowns else [])), "inputs": inputs}
    if unknowns:
        return {"state": "unknown", "why": "not known, so no rise: " + "; ".join(unknowns), "inputs": inputs}
    note = (err or {}).get("note")
    return {"state": "rise", "why": f"{window_s / 3600:g} h since the last change; every probe within {limit:g}x (T {pin['T']['probes']}, M {pin['M']['probes']}); memory {mem['pct']:+.2f}%; "
                                    f"{err['gate_5xx_and_resets']} gate 5xx or reset(s) in {err['attempts_ended']} attempt(s)" + (f"; {note}" if note else ""), "inputs": inputs}


def status_block(raw: str | None, cfg: Any, now_epoch: float | None = None) -> tuple[dict | None, list[str]]:
    """What the status shows of the level and the live check, from the store's meta value alone, and its alarm lines."""
    from .release import epoch_of
    alarms: list[str] = []
    on = bool(cfg.live_check_cmds)
    if not on and cfg.live_check_required and cfg.sandbox_image:          # also after a restart that dropped the commands, when a record of the earlier launch is in the store
        alarms.append("the LIVE CHECK (amendment 25(e)) is NOT RUNNING: this launch gives no live_check_cmds, so heavy load will not lower the total level; "
                      "set them, or set live_check_required false, which the event log says")
    if raw is None and not on:
        return None, alarms
    try:
        st = LiveState.from_json(raw)
    except ValueError as e:
        return {"state": "unreadable"}, [f"the live check's record is unreadable ({e}): the level in force is unknown"]
    caps = effective_caps(cfg, st.steps) if (st.steps == 0 or cfg.level_ladder) else {}
    lowerings = [c for c in st.changes if c["direction"] == "lower"]
    if st.steps and lowerings and lowerings[-1]["kind"] == "live_check":           # a planned step (the launch's, a restart's) is shown in the block and the render, not alarmed
        unbound = cfg.max_sandboxes is None            # a block with no entry of its own then has no cap at all, so no step reaches it
        said = ", ".join(f"{g} {c['effective']} (configured {c['configured']})" for g, c in sorted(caps.items()) if c["configured"] is not None)
        alarms.append(f"TOTAL LEVEL LOWERED by the live check: {st.steps} step(s) in force, the latest at {st.lowered_utc} ({lowerings[-1]['why']}); caps in force: {said or 'none configured'}; "
                      f"runs in flight were not stopped; it rises only by rule 29(f), one step per rise, 2 h after this change at the earliest"
                      + ("; blocks without a cap entry and no global cap are NOT bound by it" if unbound else ""))
    for s in SHAPES:
        last = st.last.get(s)
        if not last:
            continue
        if last["kind"] == "breach":
            alarms.append(f"live check {s}: the probe at {last['utc']} read {last['ratio']:.2f}x its single-run time (limit {cfg.live_check_limit:g}); "
                          f"{st.streak[s]} of {CONSECUTIVE} in a row" + (" (this one lowered the level)" if st.streak[s] == 0 else ""))
        elif last["kind"] == "unknown":
            alarms.append(f"live check {s}: the last probe ({last['utc']}) is UNKNOWN: {last['why']}")
        if st.unknown_run[s] >= 2:
            alarms.append(f"live check {s}: {st.unknown_run[s]} probes in a row are UNKNOWN: the guard cannot see {s} load, and an unknown is neither a pass nor a breach")
    if st.steps and st.rise and st.rise.get("state") in ("hold", "unknown"):
        alarms.append(f"LEVEL RISE HELD ({st.steps} step(s) below the caps, checked {st.rise['utc']}): {st.rise['why']}")
    if st.last_skip and st.last_skip.get("kind") == "no_place":
        alarms.append(f"live check: the probe found no place in the level since {st.last_skip['utc']} ({st.last_skip['why']}): it did not run")
    if on and now_epoch is not None:
        seen = [epoch_of(x["utc"]) for x in st.last.values()] + ([epoch_of(st.last_skip["utc"])] if st.last_skip else [])
        age = now_epoch - max(seen) if seen else None
        if age is not None and age > 3 * cfg.live_check_every_s + cfg.live_check_timeout_s:
            alarms.append(f"the live check last ran or was skipped {age / 60:.0f} min ago: it is not running (state unknown)")
    block = {"steps": st.steps, "max_steps": max_steps(cfg.level_ladder), "ladder": list(cfg.level_ladder), "caps": caps, "start_steps": cfg.level_start_steps,
             "changes": st.changes, "lowered_utc": st.lowered_utc, "streak": st.streak, "unknown_run": st.unknown_run, "last": st.last, "probes": st.probes, "skips": st.skips,
             "last_skip": st.last_skip, "limit": cfg.live_check_limit, "every_s": cfg.live_check_every_s, "rise_after_s": cfg.level_rise_after_s, "rise": st.rise, "memory_file": cfg.level_memory_file, "live_check_on": on,
             "history_tail": st.history[-8:]}
    return block, alarms
