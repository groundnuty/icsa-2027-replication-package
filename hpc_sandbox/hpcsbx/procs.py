"""The processes of a container, found again without a cgroup.

Docker finds them in the container's cgroup. A user on site_a has no cgroup of their own, so a container's processes are those in the pid namespaces its processes were started in:
every `apptainer exec` runs with its own pid namespace (`--containall`), the shim records the namespace's inode when its first process appears (`note_namespace`), and a process is the
container's if its /proc/<pid>/ns/pid is one of them. Not an environment marker: a cell that starts a subprocess with `env={}` would drop that. A process cannot leave its namespace.
"""
from __future__ import annotations

import os
import signal
import time
from pathlib import Path

from .common import flock, marker_of, own_pid_ns, pid_ns_inode, pids_in_ns, proc_stat, trace


def namespaces(cdir: Path) -> set:
    try:
        return {x for x in (cdir / "pidns").read_text().split() if x}
    except OSError:
        return set()


def _register(cdir: Path, ino: str) -> None:
    """Record a namespace of this container. Not in a directory that was removed meanwhile (a removal that races a start must not be undone by it)."""
    try:
        with flock(cdir / "pidns.lock", create_parent=False):
            if ino not in namespaces(cdir):
                with open(cdir / "pidns", "a") as f:
                    f.write(ino + "\n")
    except FileNotFoundError:
        pass


def _forget(cdir: Path, inodes: set) -> None:
    try:
        with flock(cdir / "pidns.lock", create_parent=False):
            keep = namespaces(cdir) - inodes
            (cdir / "pidns").write_text("".join(i + "\n" for i in sorted(keep)))
    except FileNotFoundError:
        pass


def pids(cdir: Path) -> list:
    """The container's processes: those in a pid namespace it has recorded, and those, found now, in a namespace it has not (yet) recorded whose process carries its marker (which makes
    a start that has not registered itself visible to a removal, a quiesce or a memory refresh).

    A namespace's inode number is NOT unique over time: when a namespace dies its number is free, and the next one may get it (measured: a gate's namespace took the number of a cell
    long dead, and the agent's quiesce then killed the gate). So a recorded number is believed only while no process in it carries ANOTHER container's marker; one that does has been
    reused, is forgotten, and none of its processes is this container's. A recorded namespace with no process left is forgotten too. A process with no marker (a cell's subprocess started
    with `env={}`) belongs to the container whose namespace it is in, by this rule."""
    known = namespaces(cdir)
    mine = own_pid_ns()
    name = cdir.name
    by_ns: dict = {}
    me = os.getpid()
    for e in os.listdir("/proc"):
        if e.isdigit() and int(e) != me:
            ino = pid_ns_inode(int(e))
            if ino and ino != mine:
                by_ns.setdefault(ino, []).append(int(e))
    out, stale, new = [], set(), set()
    for ino, members in by_ns.items():
        owners = {m.split(":", 1)[0] for m in (marker_of(p) for p in members) if m}
        if ino in known:
            if owners and name not in owners:
                stale.add(ino)                               # another container's: the number was reused
                continue
            out += members
        elif name in owners:
            new.add(ino)
            out += members
    if new:
        for ino in new:
            _register(cdir, ino)
    gone = stale | (known - set(by_ns))
    if gone:
        _forget(cdir, gone)
    return out


def find_main(token: str) -> "tuple | None":
    """(pid, start time) of the oldest process carrying this start's marker `HPCSBX_CID=<name>:<token>`: the container's command (a gate, the exec server), which the supervisor records."""
    want = f"HPCSBX_CID={token}".encode()
    best = None
    for e in os.listdir("/proc"):
        if not e.isdigit():
            continue
        try:
            env = Path(f"/proc/{e}/environ").read_bytes()
        except OSError:
            continue
        if want in env.split(b"\0"):
            st = proc_stat(int(e))
            if st is not None and (best is None or int(st[3]) < int(best[1])):
                best = (int(e), st[3])
    return best


def recorded_main(state: dict) -> "int | None":
    """The container's command from its record, if it is still that process (same start time). None otherwise: a pid since given to another process is not it."""
    pid = state.get("main_pid")
    if pid:
        st = proc_stat(pid)
        if st is not None and st[3] == state.get("main_start"):
            return pid
    return None


def note_namespace(cdir: Path, token: str, give_up_s: float = 20.0, stop=lambda: False) -> "str | None":
    """Find the pid namespace a container command started in and record it in `<cdir>/pidns`. Returns the inode, or None when the starter ended, or `give_up_s` passed, first.

    Why not by descent from the `apptainer` this process started: that process becomes Apptainer's setuid starter, which is root's and which `/proc` (mounted `hidepid=invisible`)
    does not show us, so the chain from it to the container's processes is not there to walk. What is there: the container's own processes are this user's, readable, and carry
    `HPCSBX_CID=<name>:<token>` in their environment (set by `apptainer_cmd`). That marker is used ONCE, to learn the namespace; membership is by the namespace after that (a cell's
    subprocess started with `env={}` is still in it). `pids()` does the same lookup lazily, so a start that this function never got to is still found."""
    mine = own_pid_ns()
    want = f"HPCSBX_CID={token}".encode()
    seen_other = set()
    deadline = time.monotonic() + give_up_s
    while time.monotonic() < deadline:
        for e in os.listdir("/proc"):
            if not e.isdigit():
                continue
            ino = pid_ns_inode(int(e))
            if not ino or ino == mine or ino in seen_other:
                continue
            try:
                env = Path(f"/proc/{e}/environ").read_bytes()
            except OSError:
                continue                                    # gone, or not readable: another's
            if want in env.split(b"\0"):
                _register(cdir, ino)
                return ino
            seen_other.add(ino)                             # another container's namespace: its processes share the namespace, so one look is enough
        if stop():
            return None
        time.sleep(0.01)
    return None


def signal_all(cdir: Path, sig: int) -> list:
    out = []
    targets = pids(cdir)
    trace("signal_all", container=cdir.name, sig=int(sig), targets={p: marker_of(p) for p in targets})
    for p in targets:
        try:
            os.kill(p, sig)
            out.append(p)
        except OSError:
            pass
    return out


def wait_gone(cdir: Path, seconds: float) -> list:
    deadline = time.monotonic() + seconds
    while True:
        left = pids(cdir)
        if not left or time.monotonic() >= deadline:
            return left
        time.sleep(0.05)


def kill_all(cdir: Path, seconds: float = 10.0) -> list:
    """SIGKILL everything of the container and wait. The survivors (a process in D state)."""
    for _ in range(5):
        signal_all(cdir, signal.SIGKILL)
        left = wait_gone(cdir, seconds / 5)
        if not left:
            return []
    return left
