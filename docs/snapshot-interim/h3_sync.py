"""A consistent copy of one audit store, made without locking the puller (lane-snap, #34).

    python h3_sync.py SRC DST            # SRC: a live audit store (m-audit, or provider-audit/<provider>); DST: our persistent copy of it

The pullers (m_audit_loop.sh, mainaudit.watch) take an exclusive non-blocking flock on ledger.lock / provider.lock and skip a round when it is held, so a reader that
locked them would cost the lead's loops a round. Instead: list every file's (size, mtime_ns) under SRC, rsync it (-rlt --checksum: a same-size file replaced within the same second must not be skipped on a retry; never --delete, the *.lock files excluded: DST keeps
extract's own outputs, runs/ leases.json summary.json platform_rows.jsonl manifests/), list again, and call the copy good only if the two listings are equal: nothing was
written in the window, and the chunk files are immutable. Otherwise try again (up to TRIES). Prints one line of counts; exit 0 stable, 1 not stable, 2 refused.
SRC is only read; DST must not be inside SRC and is created mode 700.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

TRIES = 5


def listing(root: Path) -> dict[str, tuple[int, int]]:
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".lock"):
                continue
            p = os.path.join(dirpath, f)
            try:
                st = os.stat(p)
            except FileNotFoundError:        # renamed away between the walk and the stat: the listing differs next time
                continue
            out[os.path.relpath(p, root)] = (st.st_size, st.st_mtime_ns)
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: h3_sync.py SRC DST", file=sys.stderr)
        return 2
    src, dst = Path(argv[0]).resolve(), Path(argv[1])
    if not src.is_dir():
        print(f"h3_sync: {src} is not a directory", file=sys.stderr)
        return 2
    rdst = dst.resolve()          # non-strict: a destination that does not exist yet resolves too; nothing is created before this check
    if rdst == src or str(rdst).startswith(str(src) + os.sep):
        print("h3_sync: DST is SRC or inside it: refused, nothing created", file=sys.stderr)
        return 2
    dst.mkdir(parents=True, exist_ok=True, mode=0o700)
    for attempt in range(1, TRIES + 1):
        t0 = time.time()
        before = listing(src)
        r = subprocess.run(["nice", "-n", "19", "ionice", "-c", "3", "rsync", "-rlt", "--checksum", "--exclude=*.lock", f"{src}/", f"{dst}/"], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"h3_sync: rsync rc={r.returncode}: {r.stderr.strip()[:200]}", file=sys.stderr)
            time.sleep(5)
            continue
        after = listing(src)
        if before == after:
            print(f"h3_sync ok files={len(after)} bytes={sum(s for s, _ in after.values())} tries={attempt} seconds={time.time() - t0:.1f}")
            return 0
        time.sleep(3)
    print(f"h3_sync: the store changed during every one of {TRIES} copies (the puller was writing): the copy is not known to be consistent", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
