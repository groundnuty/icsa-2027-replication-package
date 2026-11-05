"""Live 5xx and resets per option from the running sandboxes' gate logs: the gate half of the restart trigger of amendment 30(c) (correcting 29(f)), `TRIGGER` below:
op_worker is restarted on a failed health check, or when over 5% of requests were answered 5xx or reset over 5 minutes in each of two of T, T-unpaginated and D, each
with at least 100 requests in that window.

Each sandbox on THIS host has `<work_root>/<sid>/gate.json` (its option) and `<work_root>/<sid>/gatelog/requests.jsonl`, appended while it runs. What this can and
cannot see (stated in docs/opw-restart-runbook.md):
  * only options with a gate: T, T-unpaginated, D. M has none and cannot count (its signal is the live probe, which blocks the rise and lowers the level);
  * a request is logged when it ENDS. A stalled request (the gate's read timeout is 4 h) writes nothing until then, so a stall is invisible here, is printed, and
    triggers nothing; a connect or handshake timeout (60 s) ends as a logged 502 and is counted;
  * the options' counts are summed over the hosts the caller reads (this one, and each `--gate-ssh` host).
An option with fewer than `MIN_REQUESTS` requests in the window is `too_few`: neither bad nor fine. Unreadable lines are counted, not skipped silently.
"""
from __future__ import annotations

import json
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

WINDOW_S = 300.0
BAD_FRAC = 0.05          # 30(c): "over 5%", strictly
MIN_REQUESTS = 100       # 30(c): "each with at least 100 requests in that window"
GATED = ('T', 'T-unpaginated', 'D')       # the options with a gate (30(c): two of these); M has none and cannot count

# The sentence of amendment 30(c) (protocol/AMENDMENTS.md, row 30), built from the constants above so that they cannot drift from it; a test holds it to the row's
# words and to the runbook. The printouts and refusals of the restart command quote it.
TRIGGER = (f"a failed health check, or over {round(BAD_FRAC * 100)}% of requests answered 5xx or reset over {round(WINDOW_S / 60)} minutes in each of two of "
           f"{', '.join(GATED[:-1])} and {GATED[-1]}, each with at least {MIN_REQUESTS} requests in that window")


LIVE_S = 1800.0      # a sandbox whose log was written within this long counts as running, so that one with no completions in the window shows as silent


def window_counts(work_root: str | Path, *, now: float | None = None, window_s: float = WINDOW_S, live_s: float = LIVE_S) -> dict[str, dict[str, int]]:
    """{option: {requests, bad, timeouts, unreadable_lines, sandboxes}} over the last `window_s` seconds. `bad` = requests the client saw end as a 5xx or a reset.
    `sandboxes` counts those whose log changed within `live_s`: an option with sandboxes and no requests in the window is SILENT, the only live sign of a stall."""
    now = time.time() if now is None else now
    out: dict[str, dict[str, int]] = {}
    root = Path(work_root)
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        log, cfg = d / "gatelog" / "requests.jsonl", d / "gate.json"
        try:
            if log.stat().st_mtime < now - live_s:
                continue
            option = json.loads(cfg.read_text())["option"]
            text = log.read_text()
        except (OSError, ValueError, KeyError):
            continue
        c = out.setdefault(str(option), {"requests": 0, "bad": 0, "timeouts": 0, "unreadable_lines": 0, "sandboxes": 0})
        c["sandboxes"] += 1
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                t = float(r["t"])
            except (ValueError, KeyError, TypeError):
                c["unreadable_lines"] += 1
                continue
            if t < now - window_s or r.get("event") in ("request_error", "conn_close") or r.get("error_origin") == "client" and r.get("client_saw") in (None, "close"):
                continue
            if r.get("decision") == "deny":
                continue                                   # a policy refusal is the enforcement, not an error
            c["requests"] += 1
            if r.get("client_saw") in ("5xx", "reset"):
                c["bad"] += 1
                if "timed out" in str(r.get("error", "")).lower() or "timeout" in str(r.get("error", "")).lower():
                    c["timeouts"] += 1
    return out


def judge(counts: dict[str, dict[str, int]], *, frac: float = BAD_FRAC, min_requests: int = MIN_REQUESTS) -> dict[str, Any]:
    """The gate half of 30(c). {"failing": [options with at least `min_requests` requests and strictly over `frac` of them bad], "too_few": [options under `min_requests`,
    which count for nothing], "holds": bool (at least two options fail), "per_option": {...with rate}}. An option outside GATED (M) is not read. A silent option (sandboxes,
    no requests) is a stall: it is listed and never counts."""
    per, failing, few = {}, [], []
    limit = Fraction(str(frac))          # exact: 5 bad of 100 is not over 5%, and no float rounding decides it
    for o, c in sorted(counts.items()):
        if o not in GATED:
            continue
        rate = c["bad"] / c["requests"] if c["requests"] else None
        per[o] = {**c, "bad_rate": None if rate is None else round(rate, 4)}
        if c["requests"] < min_requests:
            few.append(o)
        elif c["bad"] > limit * c["requests"]:
            failing.append(o)
    silent = [o for o, c in sorted(counts.items()) if o in GATED and c["sandboxes"] and c["requests"] == 0]
    return {"failing": failing, "too_few": few, "silent": silent, "holds": len(failing) >= 2, "per_option": per,
            "blind_to": "M (no gate), the other run host, and stalled requests (logged when they end)"}


def merge(*per_host: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for h in per_host:
        for o, c in h.items():
            t = out.setdefault(o, {k: 0 for k in c})
            for k, v in c.items():
                t[k] = t.get(k, 0) + v
    return out


def remote_counts(ssh: list[str], work_root: str, *, window_s: float = WINDOW_S, run=None, timeout_s: float = 60.0) -> dict[str, dict[str, int]]:
    """The same count on another run host, read-only, by an admin ssh command (`ssh` = its argv up to the host; the lead's key). This module's own source is
    piped to `python3 -` there with the arguments below, so the two hosts count by one rule. ValueError (the reason) when the host cannot be read or answers
    something else: the caller then holds the count as incomplete, never as zero."""
    import subprocess
    run = run or subprocess.run
    src = Path(__file__).read_text()
    prog = src + f"\nimport json as _j, sys as _s\n_s.stdout.write(_j.dumps(window_counts({work_root!r}, window_s={window_s!r})))\n"
    try:
        p = run([*ssh, "nice", "-n", "19", "python3", "-"], input=prog, capture_output=True, text=True, timeout=timeout_s)
    except (subprocess.SubprocessError, OSError) as e:
        raise ValueError(f"the gate logs on {ssh[-1:]} could not be read ({type(e).__name__})") from None
    if p.returncode != 0:
        raise ValueError(f"the gate logs on {ssh[-1:]} could not be read (exit {p.returncode})")
    try:
        d = json.loads(p.stdout)
    except ValueError:
        raise ValueError(f"the gate logs on {ssh[-1:]}: the answer was not JSON") from None
    if not isinstance(d, dict):
        raise ValueError(f"the gate logs on {ssh[-1:]}: the answer was not an object")
    return d
