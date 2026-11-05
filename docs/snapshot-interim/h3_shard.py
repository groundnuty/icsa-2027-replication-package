"""One shard of extract's switched-on phase (lane-snap, #34; the lead's ruling 4 Nov: if main's cold extract is not done, start 2 shards).

    cd <main's tree> && PYTHONPATH=. python docs/snapshot-interim/h3_shard.py --store STORE --mirror MIRROR --ids IDS --shard K/N

The switched-on loop at the end of `extract()` writes `<store>/runs/<run_key>/<attempt>/switched_on.json` for every M, T, T-unpaginated and D attempt, from the run directory alone, one attempt
at a time. It is independent per attempt, so this does ONLY that loop, for every N-th pending attempt (pending = no record of the current `switched_key`; the pending list is taken from the END
of the path order, because the running extract works from the front and skips an attempt whose record already stands), straight into the same store: each file is written by rename, so
the running extract and the shards never leave a torn file, and at worst two write one file with the same content. It touches nothing else (no leases.json, no summary, no platform rows): the
running extract, or the next normal pass, writes those over the finished records. The perf-CSV size rule of h3_extract.py holds (an attempt with a CSV over H3_PERF_CSV_MAX_GIB is left to the
caller's memory cap, not built here). Prints counts only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
LIMIT = int(float(os.environ.get("H3_PERF_CSV_MAX_GIB", "1.1")) * 2 ** 30)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True, type=Path)
    ap.add_argument("--mirror", required=True, type=Path)
    ap.add_argument("--ids", required=True, type=Path)
    ap.add_argument("--shard", required=True, help="K/N")
    a = ap.parse_args(argv)
    k, n = (int(x) for x in a.shard.split("/"))
    from icsa.faults import calibrate as C
    from icsa.faults.mainaudit import __main__ as MA
    from icsa.faults.mainaudit import extract as EX
    from icsa.faults.mainaudit import switched as SW
    from icsa.faults.mainaudit import windows as W
    from icsa.faults.units import Required
    from icsa.instances import load as IL
    from icsa.records import Layout
    switched_key = f"{SW.SCHEMA}|{C.load_ids(a.ids)[1]}"
    mans = MA.manifests(a.store, a.ids)
    extents = IL.load_required_extents()
    atts = EX.attempts(a.mirror, ("M", *SW.GATED))
    pend = []
    for d, rec in atts:
        p = a.store / "runs" / W.run_key_of(rec) / d.name / "switched_on.json"
        if not EX._same_key(p, switched_key):
            pend.append((d, rec, p))
    pend.sort(key=lambda x: str(x[0]), reverse=True)
    mine = pend[k::n]
    built = skipped = 0
    t0 = time.time()
    for d, rec, p in mine:
        if EX._same_key(p, switched_key):                      # written meanwhile by the running extract or another shard
            skipped += 1
            continue
        if any(f.stat().st_size > LIMIT for f in (d / "oneclient_perf").glob("read_write_perf-*.csv")):
            skipped += 1
            continue
        r = SW.build(d, rec, required=Required.from_parted(extents[rec["run"].get("instance_id")]), manifest=mans[Layout(rec["run"]["layout"])]) | {"cache_key": switched_key}
        EX._write(p, json.dumps(r, indent=1, sort_keys=True).encode())
        built += 1
        print(f"h3_shard {k}/{n}: built={built} of {len(mine)} seconds={time.time() - t0:.0f}", flush=True)
    print(f"h3_shard {k}/{n}: pending_total={len(pend)} mine={len(mine)} built={built} skipped={skipped} seconds={time.time() - t0:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
