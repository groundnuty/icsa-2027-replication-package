#!/usr/bin/env python3
"""The process that stands in a Slurm step so that a sandbox's container runs in that step's cgroup (memory.max by the kernel, real memory.events and memory.peak).

Why a pool: a compute node cannot start a step (srun there fails: the Slurm plugin needs libjson-c.so.4, absent), and the step's cgroup is root's. Steps are started from the login node
(pool_launcher.py), one idle `stepd` per slot, with `--mem` set; a sandbox claims a free slot, hands its container command over the slot's socket, and the command runs as stepd's
child, inside the step. When the command ends stepd reports the exit status and exits, which ends the step: the next idle step is a fresh cgroup with fresh counters.

Standard library only, Python 3.6+ (the node's system Python is 3.9).

    stepd.py <HPCSBX_HOME> <kind: agent|gate> <slot> <cores, e.g. 8-11 or 4-7>

Protocol on `<home>/pool/<kind>/<slot>/ctl.sock` (one connection, one request): the client sends one JSON line
    {"argv": [...], "env_file": "<path, JSON object, mode 0600 on node tmpfs>", "cwd": ..., "stdout": "<path>", "stderr": "<path>", "oom_score_adj": N|null}
stepd answers {"pid": N} when the command is started, and {"exit": code} when it has ended (128+signal for a death by signal). The environment is read from the file, never sent over the
socket and never put in an argument list (a token must not be in `ps`). The slot directory also holds `ready.json` (written when the slot can be claimed) and, while claimed, `claimed`.
"""
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time


def atomic_write(path, text):
    tmp = "%s.%d.tmp" % (path, os.getpid())
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def parse_cores(spec):
    """"8-11" are CPU numbers; "@8-11" are INDICES into the sorted CPUs this step may use (a small holder's job owns 104-119, say, not 0-15)."""
    if spec.startswith("@"):
        allowed = sorted(os.sched_getaffinity(0))
        return {allowed[i % len(allowed)] for i in parse_cores(spec[1:])}
    out = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


def own_step_cgroup():
    """The `.../job_J/step_N/user` directory this process runs in (Slurm sets memory.max there), or None."""
    try:
        rel = [ln.split(":", 2)[2] for ln in open("/proc/self/cgroup").read().splitlines() if ln.startswith("ipv6-2")][0].strip("/")
    except (OSError, IndexError):
        return None
    parts = rel.split("/")
    for i, p in enumerate(parts):
        if p.startswith("step_"):
            return "/sys/fs/cgroup/" + "/".join(parts[:i + 1] + (["user"] if i + 1 < len(parts) and parts[i + 1] == "user" else []))
    return None


def main(argv):
    home, kind, slot, cores = argv[0], argv[1], argv[2], argv[3]
    d = os.path.join(home, "pool", kind, slot)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, mode=0o700)
    try:
        chosen = parse_cores(cores)
        os.sched_setaffinity(0, chosen)                       # the CPU limit of the sandbox: these cores (inherited by the command), not a quota
        cores = ",".join(str(c) for c in sorted(chosen))
    except OSError as e:
        sys.stderr.write("stepd: cannot pin to %s: %s\n" % (cores, e))
    sock_path = os.path.join(d, "ctl.sock")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    os.chmod(sock_path, 0o600)
    srv.listen(1)
    child = []

    def term(*_):
        for c in child:
            try:
                c.kill()
            except OSError:
                pass
        shutil.rmtree(d, ignore_errors=True)
        os._exit(143)
    signal.signal(signal.SIGTERM, term)
    cg = own_step_cgroup()
    atomic_write(os.path.join(d, "ready.json"), json.dumps({
        "pid": os.getpid(), "kind": kind, "slot": slot, "cores": cores, "cgroup": cg, "job": os.environ.get("SLURM_JOB_ID"), "step": os.environ.get("SLURM_STEP_ID"),
        "node": os.uname().nodename.split(".")[0], "memory_max": open(cg + "/memory.max").read().strip() if cg and os.path.exists(cg + "/memory.max") else None,
        "started": time.time()}))
    started = json.load(open(os.path.join(d, "ready.json")))["started"]
    while True:
        conn, _ = srv.accept()
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
        try:
            req = json.loads(buf)
        except ValueError:
            conn.close()
            continue
        if req.get("expect_started") != started:            # a claim made on an earlier step of this slot: this step is not the one the client chose
            try:
                conn.sendall((json.dumps({"exit": 126, "error": "stale slot", "stale": True}) + "\n").encode())
            except OSError:
                pass
            conn.close()
            continue
        break
    with open(req["env_file"]) as f:
        env = json.load(f)
    adj = req.get("oom_score_adj")

    def pre():
        if adj is not None:
            try:
                with open("/proc/self/oom_score_adj", "w") as fh:
                    fh.write(str(int(adj)))
            except (OSError, ValueError):
                pass
    try:
        out = open(req["stdout"], "ab")
        err = open(req["stderr"], "ab")
        c = subprocess.Popen(req["argv"], env=env, cwd=req.get("cwd") or "/", stdin=subprocess.DEVNULL, stdout=out, stderr=err, preexec_fn=pre)
    except Exception as e:  # noqa: BLE001
        conn.sendall((json.dumps({"exit": 126, "error": "%s: %s" % (type(e).__name__, e)}) + "\n").encode())
        shutil.rmtree(d, ignore_errors=True)
        return 1
    child.append(c)
    atomic_write(os.path.join(d, "claimed"), str(c.pid))
    try:
        conn.sendall((json.dumps({"pid": c.pid}) + "\n").encode())
    except OSError:
        pass                                                   # the supervisor has gone: the command is its own now; it ends with the step
    rc = c.wait()
    try:
        conn.sendall((json.dumps({"exit": rc if rc >= 0 else 128 - rc}) + "\n").encode())
    except OSError:
        pass
    shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
