"""Shared state of the Docker stand-in: where it keeps its records, locks, and the few helpers every part needs.

The stand-in runs on a site_a compute node, where Apptainer cannot run instances (`hidepid` on /proc) and a user has no network namespace, no cgroup of its own and no loop devices.
Python 3.9 is what the node has: nothing here needs more, because the shims run under the system Python.

State lives on the node's tmpfs under $HPCSBX_STATE (default /tmp/hpcsbx-<uid>/state, mode 0700): every `docker` call is its own process, so a container is a directory of files:

    containers/<name>/spec.json    what `docker run` was asked for (arguments, binds, the environment: it holds the run's tokens, hence mode 0700)
                      state.json   status, pids, StartedAt, FinishedAt, ExitCode (rewritten whole, under a lock)
                      out.log err.log   the container's stdout and stderr (`docker logs`)
                      pidns        the pid-namespace inodes of its processes (one line each): how its processes are found again
                      mnt/<tmp|shm>  fuse2fs mounts of its /tmp and /dev/shm, sized as `--tmpfs` and `--shm-size` ask
    networks/<name>.json           a "network": a subnet that decides the sandbox's loopback address, and who is on it
    images.json                    (not here: $HPCSBX_IMAGES, written once by build_images.py)
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path

UID = os.getuid()
HOME = Path(os.environ.get("HPCSBX_HOME") or f"/tmp/hpcsbx-{UID}")
STATE = Path(os.environ.get("HPCSBX_STATE") or HOME / "state")
TOOLS = Path(__file__).resolve().parents[1]                      # hpc_sandbox
PORT_OFFSET = 20000                                              # ports below 1024 cannot be bound by a user here (ip_unprivileged_port_start=1024)
APPTAINER = os.environ.get("HPCSBX_APPTAINER", "apptainer")
SERVER_VERSION = "hpcsbx-apptainer"


class ShimError(Exception):
    """A failure that `docker` would report as `Error response from daemon: ...` (exit 1)."""

    def __init__(self, msg: str, code: int = 1):
        super().__init__(msg)
        self.code = code


def ensure_dirs() -> None:
    for p in (HOME, STATE, STATE / "containers", STATE / "networks"):
        p.mkdir(parents=True, exist_ok=True)
    os.chmod(HOME, 0o700)
    os.chmod(STATE, 0o700)


def now_iso() -> str:
    t = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + f".{int((t % 1) * 1e9):09d}Z"


NEVER = "0001-01-01T00:00:00Z"


@contextlib.contextmanager
def flock(path: Path, create_parent: bool = True):
    """An exclusive lock on `path` (made if need be), released when the block ends. `create_parent=False` for a lock inside a directory that may have been removed meanwhile: it must not
    bring the directory back (FileNotFoundError then)."""
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)               # closing releases the lock


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def write_json(path: Path, obj) -> None:
    """Whole file or nothing: a reader never sees half of it."""
    path = Path(path)
    tmp = path.with_name(path.name + f".{os.getpid()}.{threading.get_ident()}.{secrets.token_hex(3)}.tmp")
    fd = os.open(str(tmp), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def container_dir(name: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,200}", name):
        raise ShimError(f"invalid container name {name!r}")
    return STATE / "containers" / name


def container_names() -> list:
    d = STATE / "containers"
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


def load_container(name: str) -> dict:
    """{"spec", "state", "dir"} or raise the daemon's own words for a container that is not there."""
    d = container_dir(name)
    spec = read_json(d / "spec.json")
    if spec is None:
        raise ShimError(f"No such container: {name}")
    return {"spec": spec, "state": read_json(d / "state.json", {}), "dir": d}


def resolve_container(ref: str) -> str:
    """A container by name, id or unique id prefix -> its name."""
    try:
        container_dir(ref)
    except ShimError:
        pass
    else:
        if (container_dir(ref) / "spec.json").exists():
            return ref
    hits = [n for n in container_names() if (read_json(container_dir(n) / "spec.json", {}) or {}).get("id", "").startswith(ref)] if len(ref) >= 4 else []
    if len(hits) == 1:
        return hits[0]
    raise ShimError(f"No such container: {ref}")


def pid_ns_inode(pid: int) -> "str | None":
    try:
        return os.readlink(f"/proc/{pid}/ns/pid")
    except OSError:
        return None


def own_pid_ns() -> str:
    return os.readlink("/proc/self/ns/pid")


def descendants_of(pid: int) -> list:
    """Every descendant of `pid`, from the parent field of /proc/<pid>/stat (this uid's processes: hidepid hides the rest, and they are not ours). Not /proc/<pid>/task/*/children,
    which needs a kernel option this node may lack."""
    by_parent: dict = {}
    for e in os.listdir("/proc"):
        if e.isdigit():
            st = proc_stat(int(e))
            if st is not None:
                by_parent.setdefault(st[1], []).append(int(e))
    out, todo = [], [pid]
    while todo:
        for c in by_parent.get(todo.pop(), ()):
            if c not in out:
                out.append(c)
                todo.append(c)
    return out


def pids_in_ns(inodes: set) -> list:
    """Host pids of this uid's processes whose pid namespace is one of `inodes` (the strings readlink gives)."""
    out = []
    me = os.getpid()
    for e in os.listdir("/proc"):
        if e.isdigit() and int(e) != me and pid_ns_inode(int(e)) in inodes:
            out.append(int(e))
    return out


def proc_stat(pid: int):
    """(state, ppid, comm, starttime) or None when the process is gone."""
    try:
        s = Path(f"/proc/{pid}/stat").read_text()
    except (OSError, ValueError):
        return None
    rest = s[s.rfind(")") + 2:].split()
    return rest[0], int(rest[1]), s[s.find("(") + 1:s.rfind(")")], rest[19]


def ns_pid(pid: int):
    """The pid as the process's own innermost namespace has it (1 = the init of a container), None when unreadable."""
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("NSpid:"):
                return int(line.split()[-1])
    except (OSError, ValueError):
        pass
    return None


def raise_nofile() -> "tuple | None":
    """Soft open-file limit up to the hard one, for what is started next: the harness asks Docker for nofile=1048576 (D and M hold a descriptor per open file), a user here can have the hard
    limit at most (51200 on a site_a node). Returns (soft, hard) now, None if it could not be set."""
    import resource
    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        if hard != resource.RLIM_INFINITY and soft < hard:
            resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
        return resource.getrlimit(resource.RLIMIT_NOFILE)
    except (OSError, ValueError):
        return None


def marker_of(pid: int) -> "str | None":
    """The `HPCSBX_CID` marker of a process (which container's start it belongs to), None when it cannot be read."""
    try:
        for e in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0"):
            if e.startswith(b"HPCSBX_CID="):
                return e[11:].decode(errors="replace")
    except OSError:
        pass
    return None


def trace(event: str, **kw) -> None:
    """One line in $STATE/signals.log for every signal this stand-in sends to a container's processes (HPCSBX_TRACE=1): when, from which command, to which pids, and which container's
    marker each of them carries. For finding out who killed what; off by default."""
    if os.environ.get("HPCSBX_TRACE") != "1":
        return
    try:
        with open(STATE / "signals.log", "a") as f:
            f.write(json.dumps({"t": now_iso(), "pid": os.getpid(), "argv": " ".join(__import__("sys").argv)[:160], "event": event, **kw}) + "\n")
    except OSError:
        pass
