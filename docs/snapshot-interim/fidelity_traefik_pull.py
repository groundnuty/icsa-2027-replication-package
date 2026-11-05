"""One bounded read of site_g's Traefik access logs for fault calibration's traefik.jsonl (lane-snap, #34; the lead's go, 5 Nov 07:05Z).

    python fidelity_traefik_pull.py --since ISO --prefix s11cal-XXXXXXXX- --out LINES [--rate-mb-s 20] [--plan-only]

`calibrate.pull_logs` greps every kept file whole (`grep -hF <run-key prefix>`, 2.2 GB now). This reads the same files, only from the line at --since on, in 4 MiB `dd` slices under nice/ionice with 0.2 s
between slices (about 20 MB/s), through the same `day0/scripts/dsk.sh` and the same pod (`calibrate._TR_EXEC`), into ONE grep, so a line cut at a slice edge is joined again. The rotated file that holds --since is
found by the rotation names (access.log.<UTC> holds nothing newer than that time) and the start inside it by a bisection of 64 KB probes on the lines' `time`; every newer file is read whole. Lines are written in file
order, oldest file first; only lines that parse as JSON and carry the prefix are kept. Prints bytes and counts only (the listing, the span read per file, the lines kept)."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

from icsa.faults import calibrate as C

BLOCK = 4 * 2 ** 20
PROBE = 65536
_TIME = re.compile(r'"time":"([^"]+)"')


def epoch(x: str) -> float:
    return dt.datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()


def dsk(cmd: str, stdin: str | None = None, timeout: int = 3600) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(C.REPO / "day0" / "scripts" / "dsk.sh"), f"{C._TR_EXEC.replace(' exec ', ' exec -i ') if stdin else C._TR_EXEC} {cmd}"],
                          input=stdin, capture_output=True, text=True, timeout=timeout, env={**__import__("os").environ, "DSK_TIMEOUT": str(timeout - 20)})


def file_size(path: str) -> int:
    p = dsk(f"stat -c %s {path}", timeout=120)
    return int(p.stdout.split()[0])


def time_at(path: str, off: int) -> float | None:
    """`time` of the first complete line in the probe that starts at `off` (a multiple of the probe size)."""
    p = dsk(f"sh -c 'dd if={path} bs={PROBE} skip={off // PROBE} count=1 2>/dev/null | sed -n 2p'", timeout=120)
    m = _TIME.search(p.stdout)
    return epoch(m.group(1)) if m else None


def start_block(path: str, size: int, since: float) -> int:
    """The BLOCK-aligned offset to start reading at: the last probe whose first complete line is older than `since`, rounded down."""
    lo, hi = 0, size // PROBE
    while hi - lo > 1:
        mid = (lo + hi) // 2
        t = time_at(path, mid * PROBE)
        if t is None:
            hi = mid        # no complete line there (a very long line or the end): look earlier
        elif t < since:
            lo = mid
        else:
            hi = mid
    return (lo * PROBE) // BLOCK


def read_span(path: str, blk0: int, size: int, prefix: str, rate_mb_s: float) -> list[str]:
    n = (size - blk0 * BLOCK + BLOCK - 1) // BLOCK
    pause = max(0.0, BLOCK / (rate_mb_s * 1e6) - 0.05)
    script = (f"i=0\n{{ while [ $i -lt {n} ]; do nice -n 19 ionice -c3 dd if={path} bs=4M skip=$((i+{blk0})) count=1 2>/dev/null; i=$((i+1)); sleep {pause:.2f}; done; }} "
              f"| grep -hF '{prefix}'\necho ICSA_PULL_RC=$?\n")
    p = dsk("sh -s", stdin=script)
    lines = p.stdout.splitlines()
    m = C._RC.match(lines[-1]) if lines else None
    if m is None or m.group(1) not in ("0", "1"):
        raise RuntimeError(f"read of {path}: no usable exit status (exit {p.returncode}): {p.stderr[-300:]}")
    return lines[:-1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rate-mb-s", type=float, default=20.0)
    ap.add_argument("--plan-only", action="store_true")
    a = ap.parse_args(argv)
    if not C.RUN_KEY_RE.match(a.prefix + "0000-x") or not a.prefix.startswith(C.PREFIX):
        raise SystemExit(f"bad run-key prefix {a.prefix!r}")
    since = epoch(a.since)
    env = {**__import__("os").environ, "DSK_TIMEOUT": "100"}
    files = C._listing(subprocess.run, C.REPO / "day0" / "scripts" / "dsk.sh", env, C._TR_EXEC, C.TRAEFIK_DIR, C.TRAEFIK_NAME)       # live file first, then the siblings by name
    plan = []
    for f in files:
        rot = None if f == C.TRAEFIK_NAME else C._rotated_at(f)
        if rot is not None and rot < since:
            continue                                     # a sibling named access.log.<UTC> holds nothing newer than that time
        path = f"{C.TRAEFIK_DIR}/{f}"
        plan.append((rot if rot is not None else float("inf"), f, path, file_size(path)))
    plan.sort()                                          # oldest first; the live file last
    # only the OLDEST file in the plan can hold lines older than --since (found by bisection): the others are read whole
    out_plan = [(f, p, (start_block(p, size, since) if i == 0 else 0), size) for i, (_, f, p, size) in enumerate(plan)]
    total = sum(size - blk * BLOCK for _, _, blk, size in out_plan)
    print(json.dumps({"files": files, "plan": [{"file": f, "from_byte": blk * BLOCK, "size": size} for f, _, blk, size in out_plan], "bytes": total}))
    if a.plan_only:
        return 0
    got: list[str] = []
    for f, path, blk, size in out_plan:
        part = [x for x in C_read(path, blk, size, a.prefix, a.rate_mb_s)]
        print(json.dumps({"file": f, "lines": len(part)}))
        got += part
    keep = []
    for x in got:
        if not x.startswith("{"):
            continue
        try:
            json.loads(x)
        except ValueError:
            continue
        keep.append(x)
    Path(a.out + ".tmp").write_text("".join(x + "\n" for x in keep))
    Path(a.out + ".tmp").replace(a.out)
    print(json.dumps({"lines_kept": len(keep), "files": files}))
    return 0


def C_read(path, blk, size, prefix, rate):
    return read_span(path, blk, size, prefix, rate)


if __name__ == "__main__":
    sys.exit(main())
