#!/usr/bin/env python3
"""Writes the M+ plan files (amendment 30(h), 33(d), science #34 12:33Z). Offline: only the frozen seeded order (numpy). No provider, no VM.
  PYTHONPATH=<frozen tree> python mplus_plans.py [--out-dir DIR]
mplus-barrier-plan.json : ONE instance per layout (the first of the seeded order); with `mplus-measure --probe` already done it makes only the whole-layout step
                          (eviction, layout provisioning, one M+ on the layout); run alone (no probe) it makes cold-site_f, M+ required AND the layout step for that instance.
mplus-resume-all.json   : all 5 instances per layout, the seeded order: the quiet window's rest when the 4 h test allows all 30 runs (done steps are skipped)
mplus-resume-reduced.json : the first 3 of the seeded order per layout (18 runs): the rest when the projected window exceeds 4 h (30(h))
The shape is the one `mplus-measure --plan` reads (`plan["instances"][layout]`) and `plan_window` writes; `check` below validates it against plan_window's own output."""
import argparse, json
from pathlib import Path
from icsa.records import Layout
from icsa.scripted import mplus as M

INST = ["I35", "I37", "I48", "I01", "I06"]          # `mplus-measure --instances` default, 30(h)'s five
SEED = 20271201
ap = argparse.ArgumentParser(); ap.add_argument("--out-dir", default=str(Path(__file__).resolve().parent)); a = ap.parse_args()
order = {la.value: M.select_instances(INST, SEED, la, None) for la in (Layout.S1, Layout.S2)}
files = {"mplus-barrier-plan.json": {la: ids[:1] for la, ids in order.items()},
         "mplus-resume-all.json": order, "mplus-resume-reduced.json": {la: ids[:M.REDUCED_N] for la, ids in order.items()}}
# the shape check: plan_window's own output (synthetic step times) has the same keys and instance lists
st = {l: {"evict_s": 10.0, "provision_required_s": 100.0, "placed_bytes_required": 1e9, "cold_site_f_wall_s": 300.0, "mplus_required_wall_s": 200.0} for l in ("S1", "S2")}
ref = M.plan_window(INST, SEED, st, {"S1": 4254680853, "S2": 3785412176})
assert ref["seeded_order"] == order and set(ref["instances"]) == {"S1", "S2"}, "the seeded order differs from plan_window's"
for name, inst in files.items():
    assert set(inst) == {"S1", "S2"} and all(inst[l] == order[l][: len(inst[l])] and inst[l] for l in inst), name
    (Path(a.out_dir) / name).write_text(json.dumps({"seed": SEED, "instances": inst, "seeded_order": order, "source": "mplus_plans.py: the frozen seeded order (30(h), 33(d))"}, indent=1) + "\n")
    print(name, inst)
