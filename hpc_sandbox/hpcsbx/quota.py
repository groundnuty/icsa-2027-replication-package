"""Size-limited filesystems without root: an ext4 image mounted by `fuse2fs` (FUSE, as the user).

The harness's disks are loop-mounted ext4 images (`hostops.make_quota_dir`): the work disk, the trace disk, and (Docker's `--tmpfs size=`, `--shm-size`) /tmp and /dev/shm. They must be real
filesystems of exactly those sizes: `Sandbox._check_capacity` adds up `statvfs` of /work, /tmp, /trace and /dev/shm inside the container and refuses a sandbox whose total could hold
a copy of the data, and a quota of the host's 189 GB tmpfs would pass that for nothing. No loop devices and no mount(2) for a user here, so fuse2fs does the mount: the root of the
filesystem is made ours (`mkfs.ext4 -E root_owner`, see bin/mkfs.ext4) and Apptainer binds the FUSE directory into the container (tested on the node, 4 Nov).
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from .common import ShimError

REAL_MKFS = "/usr/sbin/mkfs.ext4"


def _unescape(f: str) -> str:
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), f)


def mounts() -> list:
    out = []
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        pre, sep, post = line.partition(" - ")
        f = pre.split()
        if sep and len(f) >= 5:
            out.append((_unescape(f[4]), post.split()[0]))
    return out


def is_fuse_mount(path) -> bool:
    p = os.path.join(os.path.realpath(os.path.dirname(str(path))), os.path.basename(str(path)))
    return any(mp == p and fs.startswith("fuse") for mp, fs in mounts())


def mount_image(img, mnt, ro: bool = False, timeout_s: float = 20.0) -> None:
    Path(mnt).mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["fuse2fs", str(img), str(mnt), "-o", "ro" if ro else "rw"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise ShimError(f"fuse2fs {img}: exit {r.returncode}: {r.stderr.strip()[:300]}")
    deadline = time.monotonic() + timeout_s
    while not is_fuse_mount(mnt):
        if time.monotonic() > deadline:
            raise ShimError(f"fuse2fs {img}: no mount appeared at {mnt}")
        time.sleep(0.05)


def make_image(img, size_bytes: int) -> None:
    """A sparse file of `size_bytes` with a fresh ext4 filesystem, the same one `make_quota_dir` makes, its root owned by the caller."""
    Path(img).parent.mkdir(parents=True, exist_ok=True)
    with open(img, "wb") as f:
        f.truncate(size_bytes)
    r = subprocess.run([REAL_MKFS, "-q", "-F", "-m", "0", "-i", "65536", "-O", "^has_journal", "-E", f"lazy_itable_init=1,nodiscard,root_owner={os.getuid()}:{os.getgid()}", str(img)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise ShimError(f"mkfs.ext4 {img}: {r.stderr.strip()[:300]}")


def unmount(mnt, tries: int = 8) -> bool:
    """Lazily unmount everything stacked at `mnt` (a FUSE directory has one level here). True when it is no longer a mount."""
    for _ in range(tries):
        if not is_fuse_mount(mnt):
            return True
        subprocess.run(["fusermount", "-uz", str(mnt)], capture_output=True, text=True, timeout=30)
        time.sleep(0.1)
    return not is_fuse_mount(mnt)


def parse_size(text: str) -> int:
    m = re.fullmatch(r"(\d+)([kKmMgG]?)[bB]?", text.strip())
    if not m:
        raise ShimError(f"cannot read the size {text!r}")
    return int(m.group(1)) * {"": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}[m.group(2).lower()]
