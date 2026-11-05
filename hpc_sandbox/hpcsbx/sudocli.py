"""`sudo -n <command>`, for a user without sudo: what the sandbox harness runs as root, as far as a user can do it.

  * `mount -o loop,... IMG DIR` is a fuse2fs mount (quota.py); `mount --bind` and `--make-rshared` (M's oneclient mount point) cannot be done and fail, loudly;
  * `umount -l DIR` is `fusermount -uz`;
  * `chown`: the harness hands things to the agent's uid and to its own; here the agent runs as the one uid there is, so a chown to anyone else is a no-op that succeeds, and a chown
    to this user is a real one;
  * everything else (`cp`, `find`, `cat`, `mkdir`, `mv`, `rm`, `kill`, `test`, `dmesg`, `nsenter`, `sh -c`) runs as the user. What needs root and is refused (`dmesg`, `nsenter`) fails
    as it would for a user, and the harness reads that failure as "not known", which is what it is.
"""
from __future__ import annotations

import os
import sys

from . import quota
from .common import ShimError, marker_of, trace


def parse_opts(args: list) -> tuple:
    opts, pos, i = [], [], 0
    while i < len(args):
        a = args[i]
        if a == "-o" and i + 1 < len(args):
            opts += args[i + 1].split(",")
            i += 2
            continue
        if a.startswith("-"):
            opts.append(a)
        else:
            pos.append(a)
        i += 1
    return opts, pos


def do_mount(args: list) -> int:
    opts, pos = parse_opts(args)
    if "--bind" in opts or "--rbind" in opts or "--make-rshared" in opts or "--make-private" in opts or "--make-rslave" in opts:
        sys.stderr.write("mount: bind mounts and propagation changes need root; there is none here (M's oneclient mount point cannot be made by this stand-in)\n")
        return 32
    if "loop" in opts and len(pos) == 2:
        try:
            quota.mount_image(pos[0], pos[1], ro="ro" in opts)
        except ShimError as e:
            sys.stderr.write(f"mount: {e}\n")
            return 32
        return 0
    sys.stderr.write(f"mount: only loop mounts of ext4 images are implemented here: {args}\n")
    return 32


def do_umount(args: list) -> int:
    _, pos = parse_opts(args)
    rc = 0
    for p in pos:
        if not quota.unmount(p):
            sys.stderr.write(f"umount: {p}: target is busy\n")
            rc = 32
    return rc


def do_chown(args: list) -> int:
    _, pos = parse_opts(args)
    if pos and pos[0].partition(":")[0] in (str(os.getuid()), os.environ.get("USER", "\0")):
        os.execvp("chown", ["chown", *args])
    return 0


def main(argv: list) -> int:
    args = list(argv)
    while args and args[0].startswith("-") and args[0] != "--":      # sudo's own options: -n, -E, -S ...
        args.pop(0)
    if args and args[0] == "--":
        args.pop(0)
    if not args:
        sys.stderr.write("usage: sudo [-n] command\n")
        return 1
    cmd = os.path.basename(args[0])
    if cmd == "true":
        return 0
    if cmd == "mount":
        return do_mount(args[1:])
    if cmd == "umount":
        return do_umount(args[1:])
    if cmd == "chown":
        return do_chown(args[1:])
    if cmd == "kill":
        trace("sudo_kill", args=args[1:], markers={a: marker_of(int(a)) for a in args[1:] if a.isdigit()})
    os.execvp(args[0], args)
