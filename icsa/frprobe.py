"""The short fixed read before each timed block (science, #34, 2 Nov 10:07Z): so a slow build-up on site_g cannot pass unseen.

A command does the read (8 streams, 30 s, the warm study file `s2z/sst_s2.nc`, a slot user's read token: see tools/site_g_tests/read_check.py) and prints
one JSON object with `mbit_s`. The campaign and the baselines build that command in one place, `configured`, from [network] provider_port, so the read
cannot measure a different path from the runs. This module otherwise only judges the result:

    ok       the rate is at least reference x (1 - drop): dispatch of the block may start
    low      below it: the block does NOT start and the status alarms
    unknown  the command failed or timed out, printed no number, reported errors, or the reference is not configured: dispatch is HELD
    off      not configured and not required

The reference (this check on the study file, mean 4,925.1 Mbit/s since site_g's move, amendment 26(a)) and the drop (0.20: stop below 3,940.08) are CONFIG, never code: [read_check] in
config/harness.toml, with their sources.
"""
from __future__ import annotations

import json
import subprocess
from typing import Any, Callable, Sequence


def check(cmd: Sequence[str] | None, ref_mbit: float | None, drop_frac: float | None, *, required: bool = False, timeout_s: float = 180.0,
          run: Callable = subprocess.run) -> dict[str, Any]:
    out: dict[str, Any] = {"state": "unknown", "mbit_s": None, "ref_mbit_s": ref_mbit, "threshold_mbit_s": None, "why": None}
    if not cmd:
        out["state"], out["why"] = ("unknown", "no read-check command is configured") if required else ("off", None)
        return out
    if not isinstance(ref_mbit, (int, float)) or isinstance(ref_mbit, bool) or ref_mbit <= 0 or not isinstance(drop_frac, (int, float)) \
            or isinstance(drop_frac, bool) or not 0 < drop_frac < 1:
        out["why"] = "the reference rate or the allowed drop is not configured (or not a sensible number)"
        return out
    out["threshold_mbit_s"] = round(ref_mbit * (1 - drop_frac), 3)
    try:
        p = run(list(cmd), capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        out["why"] = f"the read check timed out after {timeout_s:g} s"
        return out
    except (OSError, subprocess.SubprocessError) as e:
        out["why"] = f"the read check could not run: {type(e).__name__}"
        return out
    if p.returncode != 0:
        out["why"] = f"the read check exited {p.returncode}"
        return out
    try:
        d = json.loads(p.stdout)
        v = d["mbit_s"]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v < 0:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        out["why"] = "the read check printed no rate"
        return out
    errs = d.get("errors")
    if errs not in (None, 0, {}, []):
        out["mbit_s"] = float(v)
        out["why"] = "the read check reported errors (a 5xx, a timeout or a reset): its rate is not trusted"
        return out
    out["mbit_s"] = float(v)
    out["state"] = "ok" if v >= out["threshold_mbit_s"] else "low"
    if out["state"] == "low":
        out["why"] = f"{v:g} Mbit/s is below {out['threshold_mbit_s']:g} (reference {ref_mbit:g}, drop allowed {drop_frac:.0%})"
    return out


def configured() -> dict[str, Any]:
    """The command, the reference and the drop, from config/harness.toml: the only way to them, for the campaign and the baselines alike."""
    import sys
    import tomllib
    from pathlib import Path

    from icsa.harness.real_sandbox import PROVIDER_HOST
    from icsa.sandbox import route
    port = route.configured_provider_port()
    with open(route.config_dir() / "harness.toml", "rb") as fh:
        rc = tomllib.load(fh).get("read_check", {})
    tool = Path(__file__).resolve().parents[1] / "tools" / "site_g_tests" / "read_check.py"
    return {"cmd": [sys.executable, str(tool), "--site_g-host", PROVIDER_HOST, "--site_g-port", str(port)], "port": port,
            "ref_mbit": rc.get("ref_mbit"), "drop": rc.get("drop")}


def check_configured(*, timeout_s: float = 180.0, run: Callable = subprocess.run) -> dict[str, Any]:
    """The read before a block, as configured. A configuration that cannot be read is `unknown`, which holds dispatch; it is never a crash or a pass."""
    try:
        c = configured()
    except (OSError, ValueError) as e:
        return {"state": "unknown", "mbit_s": None, "ref_mbit_s": None, "threshold_mbit_s": None, "port": None,
                "why": f"the read check's configuration cannot be read: {type(e).__name__}: {e}"}
    return {**check(c["cmd"], c["ref_mbit"], c["drop"], required=True, timeout_s=timeout_s, run=run), "port": c["port"]}


def read_warm_share(cmd: Sequence[str], *, timeout_s: float = 60.0, run: Callable = subprocess.run) -> dict[str, Any]:
    """How much of the study file is in site_g's page cache: {"warm_share": 0..1} or `fincore --bytes --noheadings --output RES,SIZE`'s "RES SIZE". Unknown if it cannot say."""
    out: dict[str, Any] = {"state": "unknown", "warm_share": None, "why": None}
    try:
        p = run(list(cmd), capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        out["why"] = f"it timed out after {timeout_s:g} s"
        return out
    except (OSError, subprocess.SubprocessError) as e:
        out["why"] = f"it could not run: {type(e).__name__}"
        return out
    if p.returncode != 0:
        out["why"] = f"it exited {p.returncode}"
        return out
    try:
        text = p.stdout.strip()
        if text.startswith("{"):
            v = json.loads(text)["warm_share"]
        else:
            res, size = text.split()[:2]
            v = int(res) / int(size)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or not 0 <= v <= 1:
            raise ValueError
    except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError):
        out["why"] = "it printed no share"
        return out
    out["state"], out["warm_share"] = "ok", float(v)
    return out
