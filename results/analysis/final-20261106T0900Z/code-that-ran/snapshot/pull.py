"""Pull the done runs' directories of a cut from the run host: `python -m snapshot.pull --out DIR --src-host HOST --bwlimit-kib N --dest-root PATH [--min-free-gib G]`.

The ONLY part of the snapshot tooling that writes outside --out, and only the run directories of `DIR/work/cut/run_dirs.txt` (the same absolute paths
on both hosts), plus its record `DIR/work/pull.json`. Low priority (ionice idle, nice 19), a bandwidth limit that is required, no delete, and each
directory's file count and bytes checked after. A directory already there is updated in place by rsync, never removed."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def argv(run_dirs: Path, src: str, dest_root: str, bwlimit_kib: int, ssh: str | None) -> list[str]:
    # -r is explicit: with --files-from, -a does not recurse, so without it each run directory arrived EMPTY (found 3 Nov)
    a = ["ionice", "-c3", "nice", "-n19", "rsync", "-a", "-r", "--no-owner", "--no-group", f"--bwlimit={bwlimit_kib}", f"--files-from={run_dirs}"]
    if ssh:
        a += ["-e", ssh]
    return a + [src, dest_root]


MIN_FREE_GIB = 20.0


def run_group(cmd: list[str], timeout: float | None = None, input_text: str | None = None) -> subprocess.CompletedProcess:
    """Runs `cmd` in its own process group and kills the whole group on a timeout or an interrupt (a hung ssh or rsync child must not outlive us)."""
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, start_new_session=True)
    try:
        out, err = p.communicate(input_text, timeout=timeout)
    except BaseException:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.communicate()
        raise
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def rsync_dir(run_dir: str, src: str, dest_root: str, bwlimit_kib: int, ssh: str | None, listfile: Path, timeout: float | None = None) -> subprocess.CompletedProcess:
    """One run directory (an absolute path on the source), at the same path below dest_root. Same command as `pull`, so the same priority, limit and no delete."""
    listfile.write_text(run_dir.lstrip("/") + "\n")
    return run_group(argv(listfile, src, dest_root, bwlimit_kib, ssh), timeout)


def _free_gib(dest_root: str, dirs: list[str]) -> float:
    """The least free space over the filesystems the run directories will land on (each directory's nearest existing ancestor below dest_root)."""
    by_dev: dict[int, float] = {}
    for d in dirs or ["/"]:
        probe = Path(dest_root) / d.lstrip("/")
        while not probe.exists():
            probe = probe.parent
        by_dev[probe.stat().st_dev] = shutil.disk_usage(probe).free / 2**30
    return min(by_dev.values())


def pull(out: Path, src_host: str | None, bwlimit_kib: int, dest_root: str, src_root: str = "/", ssh: str | None = None,
         min_free_gib: float = MIN_FREE_GIB) -> dict:
    if bwlimit_kib <= 0:
        raise SystemExit("--bwlimit-kib is required and positive")
    if not Path(dest_root).is_dir():
        raise SystemExit(f"--dest-root {dest_root} is not a directory")
    run_dirs = Path(out) / "work" / "cut" / "run_dirs.txt"
    dirs = [d for d in run_dirs.read_text().split("\n") if d]
    free = _free_gib(dest_root, dirs)
    if free < min_free_gib:
        raise SystemExit(f"refusing: {free:.1f} GiB free where the run directories land, under the floor of {min_free_gib:g} GiB (--min-free-gib)")
    src = (f"{src_host}:{src_root}" if src_host else src_root)
    # rsync --files-from takes paths relative to the source root, and --relative is implied
    rel = Path(out) / "work" / "run_dirs.rel.txt"
    rel.write_text("".join(d.lstrip("/") + "\n" for d in dirs))
    t0 = time.time()
    cmd = argv(rel, src, dest_root, bwlimit_kib, ssh)
    p = subprocess.run(cmd, capture_output=True, text=True)
    missing = [d for d in dirs if not (Path(dest_root) / d.lstrip("/")).is_dir()]
    rec = {"dest_root": dest_root, "free_gib_before": round(free, 1), "min_free_gib": min_free_gib, "command": cmd, "bwlimit_kib_s": bwlimit_kib, "src": src, "dirs": len(dirs), "missing": len(missing), "rc": p.returncode,
           "seconds": round(time.time() - t0, 1), "stderr_tail": p.stderr[-300:]}
    (Path(out) / "work" / "pull.json").write_text(json.dumps(rec, indent=1))
    return rec


def main(argv_=None) -> int:
    ap = argparse.ArgumentParser(prog="snapshot.pull")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--src-host", default=None, help="user@host of the run host; omitted: a local source (tests)")
    ap.add_argument("--bwlimit-kib", required=True, type=int)
    ap.add_argument("--dest-root", required=True, help="where the run directories are written, at their recorded absolute paths below it: use / on the host where the store says they are. No default")
    ap.add_argument("--min-free-gib", type=float, default=MIN_FREE_GIB, help=f"refuse if the destination has less free space (default {MIN_FREE_GIB:g})")
    ap.add_argument("--src-root", default="/")
    ap.add_argument("--ssh", default=None, help="the ssh command, as rsync -e takes it")
    a = ap.parse_args(argv_)
    rec = pull(a.out, a.src_host, a.bwlimit_kib, a.dest_root, a.src_root, a.ssh, a.min_free_gib)
    print(f"pull dirs={rec['dirs']} missing={rec['missing']} rc={rec['rc']} seconds={rec['seconds']}")
    return 0 if rec["rc"] == 0 and not rec["missing"] else 1


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
