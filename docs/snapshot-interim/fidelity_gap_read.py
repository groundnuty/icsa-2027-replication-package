"""One bounded read of site_g's audit log for the span our incremental store does not hold (lane-snap, #34; the lead's go, 5 Nov 07:05Z for the fault calibration's captures).

    python fidelity_gap_read.py --store DIR --since ISO --until ISO [--rate-mb-s 20] [--plan-only]

Through `icsa.faults.mainaudit`'s own backfill (so it bisects by time with 4 KB probes, reads in byte-bounded pulls under nice/ionice inside the pod, waits while .23's T live probe is above its limit, and refuses
if the log is not the file it started on): from the line at --since to the first byte at --until (found by the same bisection and written into a scratch `segment.json`, which is how `backfill --until-store`
is told where to stop). Every slot user (93), as the other ledgers; the result is a ledger like m-audit/backfill. `--plan-only` does the two bisections, prints the byte span and reads nothing else.
Prints counts only."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

from icsa.faults.mainaudit import __main__ as M
from icsa.faults.mainaudit.pull import offset_at_time


def epoch(x: str) -> float:
    return dt.datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--rate-mb-s", type=float, default=20.0)
    ap.add_argument("--max-bytes", type=int, default=64 * 2 ** 20)
    ap.add_argument("--preflight", default="/mnt/volume2/icsa-2027/m-audit/preflight/preflight.json")
    ap.add_argument("--plan-only", action="store_true")
    a = ap.parse_args(argv)
    pf = json.loads(Path(a.preflight).read_text())
    if not pf.get("ok"):
        raise SystemExit(f"{a.preflight}: the pre-flight did not pass")
    r = M._remote(pod_gzip=bool(pf.get("pod_gzip")), transport="site_g-direct")
    st = r.stat()
    start, end = offset_at_time(r, epoch(a.since)), offset_at_time(r, epoch(a.until))
    print(json.dumps({"inode": st.inode, "size": st.size, "start_off": start, "end_off": end, "bytes": end - start}))
    if a.plan_only:
        return 0
    if not 0 < end - start <= 8 * 2 ** 30:
        raise SystemExit(f"refusing: the span is {end - start} bytes")
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "segment.json").write_text(json.dumps({"start_off": end, "inode": st.inode}))
        users = M.slot_users()
        res = M.backfill(r, Path(a.store), users, epoch(a.since), max_bytes=a.max_bytes, until_store=Path(td), rate_bytes_s=a.rate_mb_s * 1e6, probe=M.probe_t_23)
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
