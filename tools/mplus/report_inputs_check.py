"""Can `mplus-report` read these --site_g-dir / --wan-dir inputs? Counts and flags only, no wall and no outcome printed.
Builds a SYNTHETIC out dir with the fake `mplus-measure` of test_mplus_run.py (all 30 steps), runs the tree's real `mplus.report` on it with the two directories, and
lists which rows get samples. On .23, from the tree, single-thread:
    cd $TREE && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=. nice -n19 $PY $L/report_inputs_check.py --site_g-dir D --wan-dir D
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

L = Path(__file__).resolve().parent
sys.path.insert(0, str(L))
import test_mplus_run as T  # noqa: E402  (its FAKE writer)
from icsa.scripted import mplus as M  # noqa: E402
from icsa.scripted.summarize import load_runs  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--site_g-dir", default="")
ap.add_argument("--wan-dir", default="")
a = ap.parse_args()
for label, d in (("site_g", a.site_g_dir), ("wan", a.wan_dir)):
    if not d:
        continue
    runs = load_runs(d)
    ms = [r for r in runs if r.get("option") == "M"]
    print(f"{label}-dir {d}: {len(runs)} records, {len(ms)} M records (whole cells {len(M.whole_cells(ms))})")
    for r in ms:
        print(f"  {r['run_key']}: layout={r.get('layout')} ok={r.get('ok')} traced={(r.get('extra') or {}).get('traced')} variant={(r.get('extra') or {}).get('variant')} "
              f"has_wall={isinstance(r.get('wall_s'), (int, float))} has_first_compute={isinstance((r.get('script') or {}).get('first_compute_s'), (int, float))}")
tmp = Path(tempfile.mkdtemp(prefix="mplus-inputs-check-"))
(tmp / "fake.py").write_text(T.FAKE)
out = tmp / "out"
order = {"S1": ["I48", "I37", "I01", "I35", "I06"], "S2": ["I48", "I01", "I06", "I35", "I37"]}
(tmp / "plan.json").write_text(json.dumps({"instances": order}))
subprocess.run([sys.executable, str(tmp / "fake.py"), "--out", str(out), "--plan", str(tmp / "plan.json")], check=True)
rep = M.report(out, site_g_dir=Path(a.site_g_dir) if a.site_g_dir else None, wan_dir=Path(a.wan_dir) if a.wan_dir else None)
print("report ran; samples per layout (n only):")
for la, d in rep["inputs"].items():
    print(f"  {la}: " + ", ".join(f"{k}={len(v)}" for k, v in d["wall_s"].items()), f"| provision required={len(d['provision_s']['required'])} layout={len(d['provision_s']['layout'])}",
          f"| failed_excluded={d['failed_runs_excluded']}")
rows = rep["break_even"]
missing = sorted(k for k, v in rows.items() if "missing" in v)
print(f"rows {len(rows)}, with an interval {len(rows) - len(missing)}, missing {len(missing)}: {missing}")
print("wan_runs:", None if rep.get("wan_runs") is None else {la: len(v) for la, v in rep["wan_runs"].items()})
