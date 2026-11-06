"""Q4 side table (lane-snap6, 6 Nov; science #34 06:07Z; ADDED AFTER SEEING THE DATA): per option x layout, the share of FINISHED runs whose reported region, baseline or target differs from the analysed extent, from `extent_account` in the pipeline's scored rows.
   python3 -I extent_account.py <seal dir> --out FILE [--rows out-coded|out|out-coded-kaug] 
extent_account is null on runs without an instrumented extent: those are COUNTED (n_extent_account_null), never dropped silently. Columns: option, layout, n_finished, n_extent_account_nonnull, n_extent_account_null, then n and share (of the non-null) for
region differs (region_matches false), baseline differs (baseline.matches false), target differs (target.matches false), any differs. Counts and rates only; no run key. Reads the seal's own files (no analysis import)."""
import csv, json, os, sys
from pathlib import Path
seal = Path(sys.argv[1]); arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
outf = arg("--out"); which = arg("--rows")
if not which:      # the coded set the seal names as primary (PRIMARY.json), else out-coded, else out; the scored rows are the pipeline's (the K-aug sets reuse out-coded's pipeline)
    which = "out-coded" if (seal / "out-coded" / "pipeline" / "scored_rows.jsonl").is_file() else "out"
src = seal / which / "pipeline" / "scored_rows.jsonl"
cells = {}
for line in open(src):
    if not line.strip():
        continue
    r = json.loads(line)
    run = r["run"]; key = (run["option"], run["layout"])
    c = cells.setdefault(key, dict(n_finished=0, nonnull=0, null=0, region=0, baseline=0, target=0, anyd=0))
    if not r.get("finished"):
        continue
    c["n_finished"] += 1
    ea = r.get("extent_account")
    if not isinstance(ea, dict):
        c["null"] += 1
        continue
    c["nonnull"] += 1
    reg = ea.get("region_matches") is False
    bas = isinstance(ea.get("baseline"), dict) and ea["baseline"].get("matches") is False
    tgt = isinstance(ea.get("target"), dict) and ea["target"].get("matches") is False
    c["region"] += reg; c["baseline"] += bas; c["target"] += tgt; c["anyd"] += (reg or bas or tgt)
rows = []
for (o, l), c in sorted(cells.items()):
    n = c["nonnull"]
    rows.append({"note": "added after seeing the data (science #34 06:07Z); share of FINISHED runs with an instrumented extent whose reported region/baseline/target differs from the analysed extent; runs without extent_account are counted, not dropped",
                 "rows_from": which, "option": o, "layout": l, "n_finished": c["n_finished"], "n_extent_account_nonnull": n, "n_extent_account_null": c["null"],
                 "n_region_differs": c["region"], "share_region_differs": c["region"] / n if n else "", "n_baseline_differs": c["baseline"], "share_baseline_differs": c["baseline"] / n if n else "",
                 "n_target_differs": c["target"], "share_target_differs": c["target"] / n if n else "", "n_any_differs": c["anyd"], "share_any_differs": c["anyd"] / n if n else ""})
Path(outf).parent.mkdir(parents=True, exist_ok=True)
with open(outf, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
os.chmod(outf, 0o600)
print(f"extent account: {len(rows)} cells, rows from {which}, finished runs {sum(c['n_finished'] for c in cells.values())} of which with extent_account {sum(c['nonnull'] for c in cells.values())} and without {sum(c['null'] for c in cells.values())}")
