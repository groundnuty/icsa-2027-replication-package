"""Claim a pre-started Slurm step (pool_launcher.py, stepd.py) for a container, and run the container's command in it.

The container's command then runs inside that step's cgroup, where Slurm has set memory.max (the kernel's OOM kill, real memory.events and memory.peak) and the cpuset; stepd pins the command
to the slot's own cores. Enabled by HPCSBX_POOL=1 in the dispatcher's environment; with it set, a gate or an agent container that cannot get a free slot FAILS (it never runs unlimited).
"""
from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

from .common import HOME, ShimError, flock, proc_stat, read_json


def enabled() -> bool:
    return os.environ.get("HPCSBX_POOL") == "1"


def kind_of(spec: dict) -> "str | None":
    if spec.get("is_gate"):
        return "gate"
    if spec.get("execd"):
        return "agent"
    return None


def _slots(kind: str) -> list:
    d = HOME / "pool" / kind
    if not d.is_dir():
        return []
    return sorted((p for p in d.iterdir() if p.is_dir()), key=lambda p: (len(p.name), p.name))


def _stale_claim(sd: Path) -> bool:
    """A claim whose owner is gone or that never got as far as starting the command: older than 60 s with no `claimed` file written by stepd, or its owner process dead."""
    c = sd / "claim"
    try:
        info = json.loads(c.read_text() or "{}")
        age = time.time() - c.stat().st_mtime
    except (OSError, ValueError):
        return False
    if (sd / "claimed").exists():
        return False
    owner = info.get("pid")
    dead = bool(owner) and (proc_stat(owner) or (None,) * 4)[3] != info.get("start")
    return dead or age > 60.0


def _limit_ok(ready: dict, want_bytes: "int | None") -> bool:
    """The slot's memory.max (read by stepd from its own cgroup) is the limit the container asked for: at least it, and at most 1% more (Slurm sets 99% of --mem; the pool is sized for main's figures).
    A slot with no cgroup or an unlimited one is never accepted when a limit was asked for."""
    if not want_bytes:
        return True
    try:
        have = int(ready.get("memory_max"))
    except (TypeError, ValueError):
        return False
    return ready.get("cgroup") is not None and want_bytes <= have <= want_bytes * 1.01


def claim(kind: str, owner: str, want_memory: "int | None" = None, wait_s: float = 180.0) -> dict:
    """A free slot of `kind` whose memory limit matches: {"dir": Path, "ready": dict}. Waits for one (a step that has just ended is replaced within a few seconds)."""
    deadline = time.monotonic() + wait_s
    me = {"owner": owner, "pid": os.getpid(), "start": (proc_stat(os.getpid()) or (None,) * 4)[3]}
    seen_mismatch = False
    while True:
        with flock(HOME / "pool" / f"{kind}.lock"):
            for sd in _slots(kind):
                ready = read_json(sd / "ready.json")
                if not ready or not (sd / "ctl.sock").exists() or proc_stat(ready["pid"]) is None:
                    continue
                if (sd / "claim").exists() and _stale_claim(sd):
                    try:
                        (sd / "claim").unlink()
                    except OSError:
                        pass
                if not _limit_ok(ready, want_memory):
                    seen_mismatch = True
                    continue
                try:
                    fd = os.open(str(sd / "claim"), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                except (FileExistsError, FileNotFoundError):
                    continue
                os.write(fd, json.dumps(me).encode())
                os.close(fd)
                return {"dir": sd, "ready": ready}
        if time.monotonic() > deadline:
            why = f" ({len(_slots(kind))} slots exist; the limit asked for is {want_memory} B and no slot has it)" if seen_mismatch and want_memory else f" ({len(_slots(kind))} slots exist)"
            raise ShimError(f"no free {kind} slot in the Slurm step pool within {wait_s:.0f} s{why}: refusing to run it without its limits")
        time.sleep(0.5)


def release(slot: dict) -> None:
    try:
        (slot["dir"] / "claim").unlink()
    except OSError:
        pass


class Conn:
    """A socket to a slot's stepd with a line buffer: two replies that arrive in one recv() are two lines."""

    def __init__(self, sock: socket.socket):
        self.s, self.buf = sock, b""

    def line(self) -> dict:
        while b"\n" not in self.buf:
            chunk = self.s.recv(65536)
            if not chunk:
                rest, self.buf = self.buf, b""
                return json.loads(rest) if rest.strip() else {}
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return json.loads(line)


def start(slot: dict, argv: list, env: dict, env_file: Path, cwd: "str | None", stdout: Path, stderr: Path, oom_score_adj: "int | None"):
    """Hand the command to the slot's stepd. Returns (Conn, started pid). ShimError(stale=True) when the slot is a newer step than the one claimed."""
    fd = os.open(str(env_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(env, f)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(30)
    s.connect(str(slot["dir"] / "ctl.sock"))
    s.sendall((json.dumps({"argv": argv, "env_file": str(env_file), "cwd": cwd, "stdout": str(stdout), "stderr": str(stderr), "oom_score_adj": oom_score_adj,
                           "expect_started": slot["ready"]["started"]}) + "\n").encode())
    c = Conn(s)
    reply = c.line()
    if "exit" in reply:
        e = ShimError(f"the step could not start the command: {reply.get('error')}")
        e.stale = bool(reply.get("stale"))
        raise e
    s.settimeout(None)
    return c, reply["pid"]


def wait(c: "Conn") -> int:
    """The command's exit status, or 137 when the step vanished (its stepd was killed, or the job ended) without saying."""
    try:
        return int(c.line().get("exit", 137))
    except (OSError, ValueError):
        return 137
