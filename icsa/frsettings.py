"""site_g's settings hash (science, #2, 2 Nov 03:54Z): the results rest on Traefik's and op_worker's image and args, and nothing else
would catch a revert. A configured command prints those fields as one JSON object; they are hashed canonically and the hash is
compared with a frozen value in a file on the run VM.

    match      the hash equals the frozen value: dispatch may go on
    mismatch   it differs: dispatch STOPS and the status alarms
    unknown    the command failed or timed out, printed no JSON object, or the frozen file is missing or malformed: dispatch HOLDS.
               Unknown never reads as a pass.
    off        not configured and not required (tests and hosts without site_g); the status says "not checked"

The site_g side is the operator's: a forced-command key on the VM that only prints the fields. Nothing here touches site_g but that command.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence

from . import opwrestart as _opw

HEX64 = re.compile(r"^[0-9a-f]{64}$")


# Keys of the printed object that are NOT settings and stay out of the hash: the free space of /data moves all the time (it has its own
# check, check_disk), and what an op_worker restart changes: the pod's restart count and start time, the process's start time and its memory
# monitor_status is provider-mon's record, not a setting. (science, #34, 3 Nov 00:24Z, the operator: op_worker may be restarted as often as needed). The restart count and start times were in the hash
# from 2 Nov 09:43Z, so that an unplanned restart stopped dispatch; that protection now lives in the restart log (icsa.opwrestart): the pod
# identity is compared with the one the log last accepted, and a restart the log does not explain stops dispatch (state "unplanned").
# The real object (site_g-config/settings-pre-resize-*.json) is {"restarts", "started", "op_worker_process_started", "rss_mb"}; the older stand-in
# names restart_count and started_at are kept so a reading in either shape separates the same way.
from .opwrestart import POD_VOLATILE
HASH_EXCLUDE = ("data_free_gb", "data_free_gib", "monitor_status") + tuple(f"op_worker_pod.{k}" for k in POD_VOLATILE)      # dotted = a key inside an object


def canonical_hash(fields: dict[str, Any], exclude: Sequence[str] = HASH_EXCLUDE) -> str:
    """sha256 over the canonical JSON (sorted keys, no spaces, UTF-8) of the fields, less the top-level keys in `exclude`."""
    kept: dict[str, Any] = {}
    for k, v in fields.items():
        if k in exclude:
            continue
        if isinstance(v, dict):
            v = {kk: vv for kk, vv in v.items() if f"{k}.{kk}" not in exclude}
        kept[k] = v
    return hashlib.sha256(json.dumps(kept, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def read_fields(cmd: Sequence[str], timeout_s: float = 20.0, run: Callable = subprocess.run) -> dict[str, Any]:
    """Run the command; raise ValueError (with the reason, never the output) unless it printed exactly one non-empty JSON object."""
    try:
        p = run(list(cmd), capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        raise ValueError(f"the command timed out after {timeout_s:g} s") from None
    except (OSError, subprocess.SubprocessError) as e:
        raise ValueError(f"the command could not run: {type(e).__name__}") from None
    if p.returncode != 0:
        raise ValueError(f"the command exited {p.returncode}")
    try:
        d = json.loads(p.stdout)
    except ValueError:
        raise ValueError("the command did not print JSON") from None
    if not isinstance(d, dict) or not d:
        raise ValueError("the command did not print a non-empty JSON object")
    return d


def read_frozen(path: str | Path) -> str:
    """The frozen hash: a file holding 64 hex characters (a trailing newline allowed). ValueError if missing or malformed."""
    try:
        t = Path(path).read_text().strip().lower()
    except OSError as e:
        raise ValueError(f"the frozen file cannot be read ({type(e).__name__})") from None
    if not HEX64.match(t):
        raise ValueError("the frozen file does not hold a sha256 (64 hex characters)")
    return t


def check(cmd: Sequence[str] | None, frozen_file: str | Path, *, required: bool = True, timeout_s: float = 20.0,
          run: Callable = subprocess.run, restart_log: str | Path | None = None, host: str = "site_g") -> dict[str, Any]:
    """{"state": match|mismatch|restart|unplanned|unknown|off, "hash", "frozen", "why"}. A hash is returned whenever the fields were read.
    With `restart_log` the pod's restart identity is compared with the log (icsa.opwrestart.state) once the hash matches: `restart` (a restart
    of ours is under way or aborted) and `unplanned` (a restart the log does not explain) stop dispatch, an unreadable log holds it."""
    out: dict[str, Any] = {"state": "unknown", "hash": None, "frozen": None, "why": None}
    if not cmd:
        if required:
            out["why"] = "no site_g settings command is configured"
        else:
            out["state"] = "off"
        return out
    try:
        fields = read_fields(cmd, timeout_s, run)
        out["hash"] = canonical_hash(fields)
        pod = fields.get("op_worker_pod") if isinstance(fields.get("op_worker_pod"), dict) else {}
        mon = fields.get("monitor") if isinstance(fields.get("monitor"), dict) else None
        ms = fields.get("monitor_status") if isinstance(fields.get("monitor_status"), dict) else {}
        # the provider monitor (tools/provider_mon.py): its static settings ("monitor") are in the hash; whether it runs now ("monitor_status") is only reported
        out["monitor"] = {"configured": mon is not None, "config_hash": (mon or {}).get("config_hash"), "running": ms.get("running"),
                          "last_sample_age_s": ms.get("last_sample_age_s")}
        out["unhashed"] = {"op_worker_rss_mb": pod.get("rss_mb"), "data_free_gb": fields.get("data_free_gb", fields.get("data_free_gib")),
                           "op_worker_restart_count": _opw.identity(fields)["restarts"],
                           "op_worker_started_at": _opw.identity(fields)["pod_started"], "op_worker_identity": _opw.identity(fields)}
    except ValueError as e:
        out["why"] = str(e)
        return out
    try:
        out["frozen"] = read_frozen(frozen_file)
    except ValueError as e:
        out["why"] = str(e)
        return out
    out["state"] = "match" if out["hash"] == out["frozen"] else "mismatch"
    if out["state"] == "mismatch":
        out["why"] = "site_g's settings differ from the frozen ones"
        return out
    if restart_log is not None:
        try:
            entries = _opw.read_log(restart_log)
        except ValueError as e:
            entries, out["state"], out["why"] = None, "unknown", str(e)
        if entries is not None:
            st, why = _opw.state(entries, host, out["unhashed"]["op_worker_identity"])
            if st != "ok":
                out["state"], out["why"] = st, why
    return out


ENV_CMD, ENV_FROZEN = "ICSA_SITE_G_SETTINGS_CMD", "ICSA_SITE_G_SETTINGS_FROZEN"
ENV_RESTART_LOG, ENV_RESTART_HOST = "ICSA_SITE_G_RESTART_LOG", "ICSA_SITE_G_RESTART_HOST"      # the scripted runs' restart log: required by check_from_env(required=True)
DEFAULT_FROZEN = "/mnt/volume2/icsa-2027/site_g_settings.frozen"


def check_from_env(required: bool = True, run: Callable = subprocess.run, timeout_s: float = 20.0) -> dict[str, Any]:
    """The scripted baselines' and the preflight's way in: the command and the frozen file from the environment. Required, it also needs the restart
    log (ICSA_SITE_G_RESTART_LOG): without it no restart could show, because the hash leaves the restart fields out, so a match is reported as unknown."""
    import os
    import shlex
    cmd = shlex.split(os.environ.get(ENV_CMD, ""))
    log = os.environ.get(ENV_RESTART_LOG) or None
    r = check(cmd or None, os.environ.get(ENV_FROZEN, DEFAULT_FROZEN), required=required, timeout_s=timeout_s, run=run,
              restart_log=log, host=os.environ.get(ENV_RESTART_HOST, "site_g"))
    if required and log is None and r["state"] == "match":
        r = {**r, "state": "unknown", "why": f"{ENV_RESTART_LOG} is not set: without the restart log an op_worker restart cannot be seen, so a timed run "
                                              f"does not start (set it to the log's path, {_opw.DEFAULT_LOG} on the run VM)"}
    return r


def require_restart_log(command: str) -> None:
    """For a timed command that does not make the full start check (the single-host curve): when site_g's settings are read there (the settings command
    is set) the restart log must be configured and readable too, because opwrestart.cut_by_restart returns None without it. Nothing configured: no-op."""
    import os
    if not os.environ.get(ENV_CMD, "").strip():
        return
    path = os.environ.get(ENV_RESTART_LOG) or None
    if path is None:
        raise SystemExit(f"{command}: refusing to start: {ENV_RESTART_LOG} is not set; without the restart log an op_worker restart cannot cut a level "
                         f"(set it to the log's path, {_opw.DEFAULT_LOG} on the run VM)")
    try:
        _opw.read_log(path)
    except ValueError as e:
        raise SystemExit(f"{command}: refusing to start: the restart log cannot be used ({e})") from None


_cache: dict[str, Any] = {"at": -1e9, "r": None}


class FrSettingsRefused(SystemExit):
    """A scripted run was about to start while site_g's settings were not the frozen ones (or could not be read)."""


def hash_for_record(max_age_s: float = 60.0, run: Callable = subprocess.run) -> str | None:
    """Called before each scripted run: stamps its record with the hash (read at most once a minute) and REFUSES to start the run when
    a command is configured and site_g's settings changed or cannot be read (unknown holds, as in the campaign). Nothing configured: None."""
    import time
    if time.monotonic() - _cache["at"] >= max_age_s:
        _cache["r"], _cache["at"] = check_from_env(required=False, run=run), time.monotonic()
    r = _cache["r"]
    if r["state"] in ("mismatch", "unknown", "restart", "unplanned"):
        raise FrSettingsRefused(f"refusing to start a run: site_g settings {r['state']} ({r['why']})")
    return r["hash"]


def check_disk(cmd: Sequence[str] | None, *, min_gib: float = 15.0, required: bool = True, timeout_s: float = 20.0,
               run: Callable = subprocess.run) -> dict[str, Any]:
    """site_g's log volume (/data: Traefik's and op_worker's logs): free GiB from a configured read-only command that prints one JSON object
    with `data_free_gib` (or a bare number). {"state": ok|low|unknown|off, "free_gib", "min_gib", "why"}. Below `min_gib` dispatch STOPS;
    an unreadable value is unknown and HOLDS it. Same forced-command key as the settings hash; nothing here touches site_g but that command."""
    out: dict[str, Any] = {"state": "unknown", "free_gib": None, "min_gib": min_gib, "why": None}
    if not cmd:
        if required:
            out["why"] = "no site_g disk command is configured"
        else:
            out["state"] = "off"
        return out
    try:
        p = run(list(cmd), capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        out["why"] = f"the command timed out after {timeout_s:g} s"
        return out
    except (OSError, subprocess.SubprocessError) as e:
        out["why"] = f"the command could not run: {type(e).__name__}"
        return out
    if p.returncode != 0:
        out["why"] = f"the command exited {p.returncode}"
        return out
    try:
        d = json.loads(p.stdout)
        v = (d.get("data_free_gib") if d.get("data_free_gib") is not None else d.get("data_free_gb")) if isinstance(d, dict) else d
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v < 0:
            raise ValueError
    except (ValueError, AttributeError):
        out["why"] = "the command did not print a free-space number"
        return out
    out["free_gib"] = float(v)
    out["state"] = "low" if v < min_gib else "ok"
    if out["state"] == "low":
        out["why"] = f"/data on site_g has {v:g} GiB free, below {min_gib:g}"
    return out


def check_exit(cmd: Sequence[str] | None, *, stop_code: int = 4, required: bool = False, timeout_s: float = 60.0,
               run: Callable = subprocess.run) -> dict[str, Any]:
    """A configured check whose EXIT CODE is its answer (`python -m icsa.faults.calibrate logcheck --out DIR`: 0 fine, 4 = the kept Traefik
    siblings are at 12 of 16 or a kept file vanished). 0 ok; `stop_code` alarm (dispatch STOPS); anything else, a timeout or a command that
    cannot run is unknown (dispatch HOLDS). Not configured: off (or unknown when required)."""
    out: dict[str, Any] = {"state": "unknown", "exit": None, "why": None}
    if not cmd:
        out["state"], out["why"] = ("unknown", "no log check command is configured") if required else ("off", None)
        return out
    try:
        p = run(list(cmd), capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        out["why"] = f"the command timed out after {timeout_s:g} s"
        return out
    except (OSError, subprocess.SubprocessError) as e:
        out["why"] = f"the command could not run: {type(e).__name__}"
        return out
    out["exit"] = p.returncode
    if p.returncode == 0:
        out["state"] = "ok"
    elif p.returncode == stop_code:
        out["state"], out["why"] = "alarm", "the log check raised its alarm (exit %d)" % stop_code
    else:
        out["why"] = f"the command exited {p.returncode}"
    return out
