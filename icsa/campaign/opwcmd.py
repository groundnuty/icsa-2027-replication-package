"""`python -m icsa.campaign opw-restart`: a person or agent restarts op_worker on site_g or site_f by the ruling of science, #34, 3 Nov 00:24Z. The campaign never
runs it by itself. It does, in this order, each step with an event in the campaign store and an entry in the restart log (icsa/opwrestart.py):

    refuse     during a named timed block (the TIMED_BLOCK file), while another restart is open, with no accepted baseline, or when the pod's identity
               is not the accepted one (an unplanned restart waits for `accept`)
    begin      dispatch pauses for ALL options: the scheduler reads the log on every look and starts nothing while a restart is open
    stop       the restart command runs; runs in flight from here are infrastructure failures in every option alike and are retried
    up         the pod identity must CHANGE (a command that exits 0 and changes nothing is an abort, not a restart) and settings must still hash the same
    checks     warm passes (reads through the read-check command, rates not judged), the op_worker memory plateau, then the read check within the
               configured drop (20%) of its reference
    end        the new identity is accepted and dispatch resumes; a failed step writes `abort` and dispatch STAYS held until an operator `accept`s

Actions: `restart` (default), `baseline` (write the accepted identity from a reading: at the freeze), `accept` (an operator's word, after an abort or a
restart done by hand). M's mounts: each run mounts oneclient inside its own sandbox, so a run that starts after `end` has a fresh mount; one in flight at
`stop` is lost with its mount. Whether a mount survives or fails cleanly is the driver tools/site_g_tests/opw_mount_test.py (needs the lead's go).

Nothing here reaches site_g except through the commands it is given: the settings command (read-only), the restart command (the operator's), and the read-check
command.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence

from icsa import frprobe, frsettings, opwrestart
from icsa.sandbox import config as sandbox_config

from . import gatewatch

TIMED_BLOCK_FILE = "/mnt/volume2/icsa-2027/TIMED_BLOCK"
EXIT_REFUSED, EXIT_ABORTED = 3, 4
LEVEL_AT_LOWEST = 3        # the level-down command's exit for 'already at the ladder's lowest' (lane-mh2: python -m icsa.campaign level-down ...)


class Refused(SystemExit):
    """The restart did not start; nothing was logged and nothing was touched."""
    def __init__(self, why: str):
        super().__init__(f"opw-restart: refused: {why}")
        self.why = why


class Aborted(SystemExit):
    """The restart started and failed; dispatch stays held until an operator accepts the state."""
    def __init__(self, why: str):
        super().__init__(f"opw-restart: ABORTED: {why}; dispatch stays held until `opw-restart --action accept`")
        self.code = EXIT_ABORTED
        self.why = why


def plateau(samples: Sequence[float], tol: float) -> bool:
    """True when the samples are level: (max - min) <= tol x mean, and there are at least 3. Rising memory is not a plateau."""
    if len(samples) < 3 or any(not isinstance(s, (int, float)) or isinstance(s, bool) or s != s or s <= 0 for s in samples):
        return False
    return (max(samples) - min(samples)) <= tol * (sum(samples) / len(samples)) and samples[-1] <= samples[0] * (1 + tol)


class Ctx:
    """Everything the steps need; tests pass stand-ins for the commands and the clock."""
    def __init__(self, *, host: str, log: str | Path, store, settings_cmd: Sequence[str], restart_cmd: Sequence[str] | None,
                 read_check: Callable[[], dict[str, Any]], run: Callable = subprocess.run, sleep: Callable[[float], None] = time.sleep,
                 timed_block_file: str | Path = TIMED_BLOCK_FILE, override_timed: str | None = None, reason: str = "",
                 warm_passes: int = 3, plateau_samples: int = 4, plateau_interval_s: float = 30.0, plateau_tol: float = 0.05,
                 plateau_max_rounds: int = 6, up_timeout_s: float = 600.0, up_poll_s: float = 10.0, restart_timeout_s: float = 900.0,
                 frozen_file: str | Path | None = None, say: Callable[[str], None] = print,
                 health: Callable[[], tuple[bool, str]] | None = None, gate_counts: Callable[[], dict[str, Any]] | None = None,
                 force: str | None = None, science_ok: str | None = None, departure: str | None = None, level_down_cmd: Sequence[str] | None = None):
        self.__dict__.update({k: v for k, v in locals().items() if k != "self"})

    def event(self, kind: str, detail: str) -> None:
        self.store.event(opwrestart.utc_now(), kind, None, detail)
        self.say(f"opw-restart [{self.host}] {kind}: {detail}")

    def entry(self, kind: str, **kw: Any) -> dict[str, Any]:
        return opwrestart.append(self.log, {"kind": kind, "host": self.host, **kw})

    def fields(self) -> dict[str, Any]:
        return frsettings.read_fields(self.settings_cmd, 30.0, self.run)


def _timed_block(ctx: Ctx) -> None:
    p = Path(ctx.timed_block_file)
    try:
        named = p.read_text().strip()
    except FileNotFoundError:
        return
    except OSError as e:
        raise Refused(f"{p} cannot be read ({type(e).__name__}): whether a timed block is running is unknown") from None
    if named and ctx.override_timed != named:
        raise Refused(f"the timed block {named!r} is named in {p}; a restart cuts it (a curve level or baseline is redone whole). "
                      f"Pass --override-timed {named} if that is intended, or wait")
    if named:
        ctx.event("opw_restart_override", f"the timed block {named!r} is named in {p}; --override-timed given by the person running this")


def _entries(ctx: Ctx) -> list[dict[str, Any]]:
    try:
        return opwrestart.read_log(ctx.log)
    except ValueError as e:
        raise Refused(str(e)) from None


def _need_process_start(ident: dict[str, Any]) -> None:
    if not opwrestart.has_process_start(ident):
        raise Refused("the settings command printed no op_worker process start: a restart inside the pod moves only that, so an identity without it "
                      "could not show one (nothing was written)")


def baseline(ctx: Ctx) -> int:
    """Write the accepted identity from a reading: at the freeze, with the frozen hash read alongside it. Once per host: a later one is refused,
    because the reference moves only by a restart this command ran or by `accept`."""
    f = ctx.fields()
    ident = opwrestart.identity(f)
    if all(v is None for v in ident.values()):
        raise Refused("the settings command printed no op_worker pod identity")
    _need_process_start(ident)
    if Path(ctx.log).exists() and opwrestart.accepted(_entries(ctx), ctx.host) is not None:
        raise Refused(f"the restart log already holds an accepted identity for {ctx.host}: a baseline is written once, at the freeze. To move the "
                      "reference after a state you have checked, run --action accept --reason \"<what you saw>\"")
    e = ctx.entry("baseline", identity=ident, hash=frsettings.canonical_hash(f), reason=ctx.reason)
    ctx.event("opw_baseline", f"accepted identity {ident} (hash {e['hash']})")
    return 0


def accept(ctx: Ctx) -> int:
    """An operator's word that the identity now seen is the intended one (after an abort, or a restart done by hand)."""
    f = ctx.fields()
    ident = opwrestart.identity(f)
    if all(v is None for v in ident.values()):
        raise Refused("the settings command printed no op_worker pod identity")
    _need_process_start(ident)
    ctx.entry("accept", identity=ident, hash=frsettings.canonical_hash(f), reason=ctx.reason)
    ctx.event("opw_accept", f"accepted identity {ident}: {ctx.reason or 'no reason given'}")
    return 0


def condition(ctx: Ctx) -> tuple[bool, str]:
    """Amendment 30(c), correcting 29(f): `gatewatch.TRIGGER`. Slowness alone is never one, M cannot count, and a stall is printed and triggers nothing.
    Returns (holds, the evidence in words). What the gate count cannot see is part of the words."""
    parts, holds = [], False
    if ctx.health is not None:
        ok, why = ctx.health()
        parts.append(f"health check {'passed' if ok else 'FAILED'}: {why}")
        holds = holds or not ok
    if ctx.gate_counts is not None:
        try:
            j = gatewatch.judge(ctx.gate_counts())
        except ValueError as e:        # a host could not be read: the count is incomplete, so it is printed as unknown and NOT enforced (use --force)
            parts.append(f"gate logs UNKNOWN, not enforced: {e}")
        else:
            parts.append(f"gate logs, last 5 min: {json.dumps(j['per_option'], sort_keys=True)}; options over 5%: {j['failing']}; "
                         f"too few requests (fewer than {gatewatch.MIN_REQUESTS} in the window, so not counted): {j['too_few']}; "
                         f"NO COMPLETIONS in the window (sandboxes running, a possible stall; a stall writes nothing, is printed, and triggers nothing; never a trigger): {j['silent']}; "
                         f"blind to {j['blind_to']}")
            holds = holds or j["holds"]
    if not parts:
        parts.append("no health check and no gate count configured: the condition cannot be read")
    return holds, "; ".join(parts)


def in_flight_by_option(store) -> dict[str, int]:
    """Runs whose attempt is running now, by option: what a restart would turn into infrastructure failures."""
    out: dict[str, int] = {}
    for r in store.q("SELECT r.option, COUNT(*) n FROM attempts a JOIN runs r ON r.run_key=a.run_key WHERE a.state='running' GROUP BY r.option"):
        out[r["option"]] = r["n"]
    return out


def restart(ctx: Ctx) -> int:
    if not ctx.restart_cmd:
        raise Refused("no restart command given (--restart-cmd)")
    if not ctx.reason.strip():
        raise Refused(f"say why (--reason): the trigger of amendment 30(c) is {gatewatch.TRIGGER}; never one slow option or run, a stall, or M alone. "
                      "Any other restart goes to the science agent first")
    _timed_block(ctx)
    holds, evidence = condition(ctx)
    forced = None
    if not holds:
        discard = in_flight_by_option(ctx.store)
        msg = (f"amendment 30(c): the condition does not hold ({evidence}). The trigger is {gatewatch.TRIGGER}. Slow reads only pause or lower dispatch. "
               f"Any other restart goes to the science agent first. A force would discard the runs in flight: "
               f"{json.dumps(discard, sort_keys=True)} (infrastructure failures, retried). To force: --force-reason \"<why>\" and either --science-ok <the science agent's comment URL> "
               "or --departure \"<every live probe's state>\" (the lead's: science has not answered within 15 minutes and every live probe is failing); both are recorded")
        if not (ctx.force or "").strip():
            raise Refused(msg)
        if bool((ctx.science_ok or "").strip()) == bool((ctx.departure or "").strip()):
            raise Refused("a force needs exactly one of --science-ok <comment URL> and --departure \"<probes' state>\"; " + msg)
        if ctx.science_ok and not ctx.science_ok.startswith("https://github.com/"):
            raise Refused("--science-ok must be the URL of science's comment on GitHub")
        forced = {"reason": ctx.force.strip(), **({"science_ok": ctx.science_ok.strip()} if ctx.science_ok else {"departure": ctx.departure.strip()}),
                  "discarded_in_flight": discard}
    entries = _entries(ctx)
    busy = opwrestart.in_progress(entries, ctx.host)
    if busy:
        raise Refused(busy)
    acc = opwrestart.accepted(entries, ctx.host)
    if acc is None:
        raise Refused(f"the log holds no accepted identity for {ctx.host}: run --action baseline at the freeze")
    try:
        pre = ctx.fields()
    except ValueError as e:
        raise Refused(f"the settings cannot be read before the restart ({e}): the identity before it would be unknown") from None
    before = opwrestart.identity(pre)
    _need_process_start(before)
    if before != acc:
        raise Refused(f"the pod's identity {before} is not the accepted {acc}: an unplanned restart waits for --action accept")
    hash_before = frsettings.canonical_hash(pre)
    no = opwrestart.completed(entries, ctx.host) + 1

    ctx.entry("begin", restart_no=no, reason=ctx.reason, identity_before=before, evidence=evidence, forced=forced)
    ctx.event("opw_restart_begin", f"#{no}: {ctx.reason}; {'FORCED ' + json.dumps(forced, sort_keys=True) if forced else 'condition holds'}; evidence: {evidence}; dispatch pauses for all options; identity before {before}")
    try:
        ctx.entry("stop", restart_no=no)
        ctx.event("opw_restart_stop", f"#{no}: running the restart command; runs in flight from now are infrastructure failures, retried in every option alike")
        try:
            p = ctx.run(list(ctx.restart_cmd), capture_output=True, text=True, timeout=ctx.restart_timeout_s)
        except subprocess.TimeoutExpired:
            raise Aborted(f"the restart command timed out after {ctx.restart_timeout_s:g} s") from None
        except (OSError, subprocess.SubprocessError) as e:
            raise Aborted(f"the restart command could not run ({type(e).__name__})") from None
        if p.returncode != 0:
            raise Aborted(f"the restart command exited {p.returncode}")
        after, f_after = _wait_for_new_identity(ctx, before)
        ctx.entry("up", restart_no=no, identity=after)
        ctx.event("opw_restart_up", f"#{no}: op_worker answers with a new identity {after}")
        hash_after = frsettings.canonical_hash(f_after)
        if hash_after != hash_before:
            raise Aborted(f"the settings hash changed across the restart ({hash_before[:12]} -> {hash_after[:12]}): something besides the restart fields differs")
        if ctx.frozen_file is not None:
            try:
                if hash_after != frsettings.read_frozen(ctx.frozen_file):
                    raise Aborted("the settings hash after the restart is not the frozen one")
            except ValueError as e:
                raise Aborted(f"the frozen hash cannot be compared ({e})") from None
        checks = _checks(ctx)
        if ctx.level_down_cmd:      # dispatch returns one level lower (science, #34, 00:28Z), set BEFORE `end` lets it resume
            try:
                p = ctx.run([*ctx.level_down_cmd, "--reason", f"op_worker restart #{no} on {ctx.host}: {ctx.reason}"], capture_output=True, text=True, timeout=120.0)
            except (subprocess.SubprocessError, OSError) as e:
                raise Aborted(f"the level-down command could not run ({type(e).__name__})") from None
            if p.returncode == LEVEL_AT_LOWEST:      # lane-mh2's command: already at the ladder's lowest, nothing changed. Holding forever would be worse: a warning, not an abort
                ctx.event("opw_restart_level_down", f"#{no}: WARNING: dispatch is already at the lowest level, nothing was lowered")
                checks["level_down"] = "already_at_lowest"
            elif p.returncode != 0:
                raise Aborted(f"the level-down command exited {p.returncode}: dispatch would have resumed at the old level")
            else:
                ctx.event("opw_restart_level_down", f"#{no}: dispatch set one level lower")
                checks["level_down"] = True
    except Aborted as a:
        ctx.entry("abort", restart_no=no, why=a.why)
        ctx.event("opw_restart_abort", f"#{no}: {a.why}")
        raise
    ctx.entry("end", restart_no=no, identity=after, hash=hash_after, checks=checks)
    ctx.event("opw_restart_end", f"#{no}: checks passed ({json.dumps(checks, sort_keys=True)}); dispatch resumes with the new identity {after}")
    return 0


def _wait_for_new_identity(ctx: Ctx, before: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    t_end = time.monotonic() + ctx.up_timeout_s
    last = "no reading yet"
    while True:
        try:
            f = ctx.fields()
            now = opwrestart.identity(f)
            if now != before and opwrestart.has_process_start(now):
                return now, f
            last = ("the new identity has no readable process start yet" if now != before
                    else "the identity is still the one from before the restart")
        except ValueError as e:
            last = str(e)
        if time.monotonic() >= t_end:
            raise Aborted(f"op_worker did not come back with a new identity within {ctx.up_timeout_s:g} s ({last}); a command that exits 0 and changes nothing is not a restart")
        ctx.sleep(ctx.up_poll_s)


def _rss(ctx: Ctx) -> float | None:
    try:
        v = (ctx.fields().get("op_worker_pod") or {}).get("rss_mb")
    except ValueError:
        return None
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _checks(ctx: Ctx) -> dict[str, Any]:
    """Warm passes, memory plateau, read check: the three conditions before dispatch resumes (ruling, item 3)."""
    warm = []
    for i in range(ctx.warm_passes):
        r = ctx.read_check()
        warm.append(r.get("mbit_s"))
        ctx.event("opw_restart_warm", f"warm pass {i + 1}/{ctx.warm_passes}: {r.get('state')} {r.get('mbit_s')} Mbit/s {r.get('why') or ''}".rstrip())
        if r.get("state") == "unknown":
            raise Aborted(f"warm pass {i + 1} could not read ({r.get('why')})")
    samples: list[float] = []
    for rnd in range(ctx.plateau_max_rounds):
        v = _rss(ctx)
        if v is not None:
            samples.append(v)
        samples = samples[-ctx.plateau_samples:]
        if len(samples) >= ctx.plateau_samples and plateau(samples, ctx.plateau_tol):
            break
        ctx.sleep(ctx.plateau_interval_s)
    else:
        raise Aborted(f"op_worker memory did not plateau in {ctx.plateau_max_rounds} rounds (last samples {samples} MB, tolerance {ctx.plateau_tol:g})")
    ctx.event("opw_restart_plateau", f"op_worker rss levelled at {samples} MB")
    rc = ctx.read_check()
    ctx.event("opw_restart_read_check", f"{rc.get('state')}: {rc.get('mbit_s')} Mbit/s, threshold {rc.get('threshold_mbit_s')}, reference {rc.get('ref_mbit_s')} {rc.get('why') or ''}".rstrip())
    if rc.get("state") != "ok":
        raise Aborted(f"the read check after the restart is {rc.get('state')} ({rc.get('mbit_s')} Mbit/s, threshold {rc.get('threshold_mbit_s')}): {rc.get('why')}")
    return {"warm_mbit_s": warm, "rss_mb": samples, "read_mbit_s": rc.get("mbit_s"), "read_ref_mbit_s": rc.get("ref_mbit_s"),
            "read_threshold_mbit_s": rc.get("threshold_mbit_s")}


def _gate_counts(a):
    """This host's sandboxes plus each `--gate-ssh LABEL=ssh argv` host's (read-only, by the lead's admin ssh). A host that cannot be read makes the count unknown."""
    root = a.work_root or str(sandbox_config.DATA_ROOT / "sandboxes")
    remotes = [(x.split("=", 1)[0], shlex.split(x.split("=", 1)[1])) for x in (a.gate_ssh or [])]

    def counts() -> dict[str, Any]:
        per = [gatewatch.window_counts(root)]
        for label, ssh in remotes:
            per.append(gatewatch.remote_counts(ssh, root))
        return gatewatch.merge(*per)
    return counts


def _health(a):
    import importlib
    mod, fn = a.health.split(":")
    return getattr(importlib.import_module(mod), fn)


ACTIONS = {"restart": restart, "baseline": baseline, "accept": accept}


def main(a, store) -> int:
    """From the CLI: the settings command is the environment's, as for the campaign's own check."""
    settings_cmd = shlex.split(os.environ.get(frsettings.ENV_CMD, ""))
    if not settings_cmd:
        raise SystemExit(f"opw-restart: {frsettings.ENV_CMD} is not set: the pod's identity cannot be read")
    ctx = Ctx(host=a.host, log=a.restart_log or os.environ.get(opwrestart.ENV_LOG) or opwrestart.DEFAULT_LOG, store=store, settings_cmd=settings_cmd,
              restart_cmd=shlex.split(a.restart_cmd) if a.restart_cmd else None,
              read_check=lambda: frprobe.check_configured(timeout_s=180.0), timed_block_file=a.timed_block_file,
              override_timed=a.override_timed, reason=a.reason or "", warm_passes=a.warm_passes,
              plateau_interval_s=a.plateau_interval_s, up_timeout_s=a.up_timeout_s,
              frozen_file=os.environ.get(frsettings.ENV_FROZEN, frsettings.DEFAULT_FROZEN), force=a.force_reason, science_ok=a.science_ok, departure=a.departure,
              level_down_cmd=shlex.split(a.level_down_cmd) if a.level_down_cmd else None,
              health=_health(a) if a.host == "site_g" else None,
              gate_counts=_gate_counts(a))
    return ACTIONS[a.action](ctx)
