"""The memory that is really there: the Slurm job's cgroup, not the node.

A held job is killed by the kernel at its cgroup's `memory.max` (285 GiB for the job on node_1, 126.7 GiB for the one on node_1), whatever `/proc/meminfo` says: both nodes show
the whole 377 GiB node, which other jobs share. The sandboxes' disks are tmpfs (RAM) and tmpfs pages are charged to the cgroup that wrote them, so they count here too. The harness's
host-memory hold (`icsa.campaign.hostmem`) reads MemAvailable from /proc/meminfo; the override points it at `available()`, the room left in this job.
"""
from __future__ import annotations

from pathlib import Path

CGROOT = Path("/sys/fs/cgroup")


def job_cgroup() -> "Path | None":
    """The `job_<id>` cgroup directory of this process (a step's directory is below it), None outside a Slurm job."""
    try:
        rel = [ln.split(":", 2)[2] for ln in Path("/proc/self/cgroup").read_text().splitlines() if ln.startswith("ipv6-2")][0].strip("/")
    except (OSError, IndexError):
        return None
    parts = rel.split("/")
    for i, name in enumerate(parts):
        if name.startswith("job_"):
            return CGROOT.joinpath(*parts[:i + 1])
    return None


def _read(path: Path) -> "int | None":
    try:
        v = path.read_text().strip()
        return None if v == "max" else int(v)
    except (OSError, ValueError):
        return None


def limit() -> "int | None":
    d = job_cgroup()
    return _read(d / "memory.max") if d else None


def current() -> "int | None":
    d = job_cgroup()
    return _read(d / "memory.current") if d else None


def node_available() -> "int | None":
    """MemAvailable of the node in bytes (the harness's own reader, copied: the original is replaced by `available` and must not be called back)."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def available() -> "int | None":
    """Bytes left under the job's limit, or None when it cannot be read (the caller then does not know: the hold keeps its state). The smaller of this and the node's MemAvailable."""
    lim, cur = limit(), current()
    if lim is None or cur is None:
        return None
    node = node_available()
    room = max(0, lim - cur)
    return room if node is None else min(room, node)
