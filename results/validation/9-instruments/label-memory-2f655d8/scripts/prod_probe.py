"""process_run through the real Production on real run directories: real required extent, real reference (frozen truth, SST recomputed), real index.
Each stage timed. usage: prod_probe.py [--data-dir DIR] RUN [RUN...] (each RUN: dir with a run record; a copy with a record is made if needed)"""
import argparse, json, resource, sys, time
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("runs", nargs="+"); ap.add_argument("--data-dir"); ap.add_argument("--mark"); a = ap.parse_args()
def peak(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
T = [time.time()]
def stage(n):
    now = time.time(); print(f"STAGE {n}: {now - T[-1]:.1f} s, peak so far {peak():.2f} GiB", flush=True); T.append(now)
from icsa.pipeline.postrun import process_run
from icsa.pipeline.resources import Production
from icsa.pipeline.loadrec import read_record
kw = {"data_dir": Path(a.data_dir)} if a.data_dir else {}
res = Production(**kw); stage("Production()")
res.index(None); stage("index")
for r in a.runs:
    d = Path(r); rec, _ = read_record(d); key = rec.run.key()
    res.required(rec.run.instance_id); stage(f"{key}: reference and required")
    e = {"run_dir": str(d), "key": key, "run_key": f"main__{key}", "block": "main", "attempt": 1}
    p = process_run(e, {"exclude_from_analysis": 0}, res); stage(f"{key}: process_run")
    c = p.coding
    print("RESULT", key, json.dumps({"label": p.label.value, "reasons": p.reasons, "finished": p.row.finished, "report_valid": p.row.report_valid, "exact": getattr(p.row, "exact", None),
          "cause": getattr(c, "primary", None), "skipped": getattr(c, "reason", None), "not_observed": p.label_row["not_observed"], "platform": p.label_row["platform_evidence"], "observed": p.label_row["observed"],
          "xcheck": {k: p.label_row.get(k) for k in ("listing_disagrees", "decoded_not_delivered", "delivered_not_decoded")}}, default=str)[:900], flush=True)
print(f"TOTAL {time.time() - T[0]:.1f} s, peak {peak():.2f} GiB")
