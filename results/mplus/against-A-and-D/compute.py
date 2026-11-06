"""M+ break-even against options T and D (and M, like-for-like), 3 instances with T and D records.

Reuses the frozen functions as they are (icsa.scripted.mplus.break_even_inputs, icsa.scripted.breakeven.bootstrap_interval,
json_safe); only the INPUTS are filtered before the calls. Run:
  PYTHONPATH=<frozen tree> <frozen tree>/.venv/bin/python compute.py
Nothing is written outside this directory. Descriptive; added after seeing the data.
"""
from __future__ import annotations

import copy
import csv
import datetime
import glob
import hashlib
import inspect
import json
import math
import subprocess
from pathlib import Path

from icsa.scripted import breakeven as BE
from icsa.scripted import mplus as MP
from icsa.scripted import summarize as SM

TREE = Path("~/work/wt/fill-09ecc2c0")
MIRROR = Path("/mnt/volume2/icsa-2027/mplus-mirror/f1c242a")
STEPA = Path("/mnt/volume2/icsa-2027/launch-checks/baselines-f1c242a")
OUT = Path(__file__).resolve().parent

SEED = inspect.signature(MP.report).parameters["seed"].default          # report(): the seed the M+ report used
N_BOOT = inspect.signature(BE.bootstrap_interval).parameters["n_boot"].default   # report() passes only the seed
LEVEL = inspect.signature(BE.bootstrap_interval).parameters["level"].default
LAYOUTS = ("S1", "S2")
SCOPES = ("required", "layout")
COMPARATORS = ("T", "D", "M")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def line_of(fn) -> str:
    src, first = inspect.getsourcelines(fn)
    return f"{Path(inspect.getsourcefile(fn)).relative_to(TREE)}:{first}-{first + len(src) - 1}"


log = [json.loads(x) for x in (MIRROR / "mplus_log.jsonl").read_text().splitlines()]
mruns = SM.load_runs(MIRROR)
aruns = SM.load_runs(STEPA)
existing = json.loads((MIRROR / "breakeven.json").read_text())
assert existing["seed"] == SEED, (existing["seed"], SEED)

# --- the instance set: instances with an ok T, D and M record in step A (whole cells) ---------------------------------------
have = {o: {r["instance_id"] for r in MP.whole_cells(aruns) if r["option"] == o and r["ok"]} for o in ("T", "D", "M")}
INST = frozenset(have["T"] & have["D"] & have["M"])
assert INST == {"I35", "I37", "I48"}, INST
INST_STR = ";".join(sorted(INST))

# --- which instances each layout-scope provision event served (log order; sensitivity only) --------------------------------
run_inst = {r["run_key"]: r["instance_id"] for r in mruns}
served: dict[int, list[str]] = {}
cur = None
for i, e in enumerate(log):
    if e.get("event") == "provision":
        cur = i if e["scope"] == "layout" else None
        if cur is not None:
            served[cur] = []
    elif e.get("event") == "mplus_run" and e.get("scope") == "layout" and cur is not None:
        served[cur].append(run_inst[e["run_key"]])


def inputs(insts, comparator: str, layout_p: str = "all") -> dict:
    """break_even_inputs on inputs restricted to `insts`. The comparator's step-A records are relabelled option "M" in COPIES,
    because break_even_inputs reads only option == "M" from site_g_runs (it is the cold-site_g column); nothing else is changed.
    layout_p "all": every layout-scope provision event (no instance is recorded on them). "served": only those events that
    preceded at least one layout-scope M+ run on `insts`."""
    plog = []
    for i, e in enumerate(log):
        if e.get("event") == "provision":
            if e["scope"] == "required" and e["instance"] not in insts:
                continue
            if e["scope"] == "layout" and layout_p == "served" and not (set(served[i]) & insts):
                continue
        plog.append(e)
    runs = [r for r in mruns if r["instance_id"] in insts]
    site_g = []
    for r in aruns:
        if r["instance_id"] in insts and r["option"] == comparator:     # exact match: T-unpaginated is not T
            q = copy.deepcopy(r)
            q["option"] = "M"
            site_g.append(q)
    return MP.break_even_inputs(plog, runs, site_g_runs=site_g)


def interval(d: dict, scope: str) -> dict:
    """The same call and the same missing-samples branch as report()."""
    p, c, w = d["provision_s"][scope], d["wall_s"]["cold-site_g"], d["wall_s"][f"mplus-{scope}"]
    return (BE.bootstrap_interval(p, c, w, seed=SEED) if p and c and w
            else {"missing": {"provision": len(p), "cold": len(c), "mplus": len(w)}})


def fmt(v):
    if isinstance(v, float) and math.isfinite(v) and v == int(v):
        return str(int(v))
    return str(v)


def independent(comparator: str, layout: str, scope: str, insts) -> tuple[list, list, list]:
    """P, C, W again, from the raw files by another route (log events, run_key globs), to cross-check the function path."""
    c = []
    for iid in sorted(insts):
        for p in glob.glob(str(STEPA / "runs" / f"s12-base-enf-p?-{iid}-{comparator}-{layout}-a1" / "run.json")):
            r = json.loads(Path(p).read_text())
            assert r["option"] == comparator and r["ok"]
            c.append(r["wall_s"])
    pp = [e["seconds"] for e in log if e.get("event") == "provision" and e["layout"] == layout and e["scope"] == scope
          and e.get("confirmed_placed") is True and (scope == "layout" or e["instance"] in insts)]
    w = []
    for e in log:
        if e.get("event") == "mplus_run" and e["scope"] == scope and e["ok"]:
            f = json.loads((MIRROR / "runs" / e["run_key"] / "run.json").read_text())
            if f["layout"] == layout and f["instance_id"] in insts:
                assert f["wall_s"] == e["wall_s"]
                w.append(e["wall_s"])
    return pp, c, w


rows, sens, checks = [], [], []
for layout in LAYOUTS:
    for scope in SCOPES:
        for comp in COMPARATORS:
            d = inputs(INST, comp)[layout]
            b = interval(d, scope)
            assert "missing" not in b, (layout, scope, comp, b)
            assert (b["n_p"], b["n_c"], b["n_w"]) == (3, 3, 3), (layout, scope, comp, b["n_p"], b["n_c"], b["n_w"])
            pp, cc, ww = independent(comp, layout, scope, INST)
            assert sorted(pp) == sorted(d["provision_s"][scope]) and sorted(cc) == sorted(d["wall_s"]["cold-site_g"]) \
                and sorted(ww) == sorted(d["wall_s"][f"mplus-{scope}"]), (layout, scope, comp)
            assert math.isclose(b["mean_c"], sum(cc) / len(cc)) and math.isclose(b["mean_w"], sum(ww) / len(ww)) \
                and math.isclose(b["mean_p"], sum(pp) / len(pp))
            note = (f"C = step-A {comp} wall_s, cold-site_g, traced, slot token" if comp != "M" else
                    "like-for-like reference: C = step-A M wall_s (cold-site_g), same 3 instances")
            note += ("; P = the 3 required-scope provision events of these instances" if scope == "required" else
                     "; P = all 3 layout-scope provision events (no instance is recorded on them; one event served 1-2 instances)")
            note += f"; W = M+ {scope}-scope walls of these instances; CI = percentile bootstrap, {N_BOOT} draws, level {LEVEL}, seed {SEED}"
            if b["share_no_break_even"] > 0:
                note += f"; {b['share_no_break_even']:.4f} of bootstrap draws have no break-even"
            if b["point"] == math.inf:
                note += "; point: mean C <= mean W, no break-even"
            rows.append({"layout": layout, "scope": scope, "comparator": comp, "instances": INST_STR,
                         "n_P": b["n_p"], "n_C": b["n_c"], "n_W": b["n_w"], "break_even": b["point"],
                         "ci_lo": b["low"], "ci_hi": b["high"], "note": note,
                         "_detail": b, "_excluded": {"failed_runs_excluded": d["failed_runs_excluded"],
                                                     "unconfirmed_provisioning_excluded": d["unconfirmed_provisioning_excluded"]}})
            if scope == "layout":
                ds = inputs(INST, comp, "served")[layout]
                bs = interval(ds, scope)
                sens.append({"layout": layout, "scope": scope, "comparator": comp, "instances": INST_STR,
                             "n_P": bs["n_p"], "n_C": bs["n_c"], "n_W": bs["n_w"], "break_even": bs["point"],
                             "ci_lo": bs["low"], "ci_hi": bs["high"], "_detail": bs})

# --- reproduction check: all 5 M+ instances, step-A M as cold-site_g, against the registered breakeven.json ---------------------
ALL5 = frozenset(r["instance_id"] for r in mruns)
repro = []
for layout in LAYOUTS:
    for scope in SCOPES:
        got = BE.json_safe(interval(inputs(ALL5, "M")[layout], scope))
        want = existing["break_even"][f"{layout}/{scope}/cold-site_g"]
        repro.append({"cell": f"{layout}/{scope}/cold-site_g", "identical": got == want,
                      "keys_differing": sorted(k for k in set(got) | set(want) if got.get(k) != want.get(k))})
repro_ok = all(x["identical"] for x in repro)

# --- the step-A M walls against the registered table's cold-site_g inputs, value by value --------------------------------------
same_m = all(sorted(inputs(INST, "M")[la]["wall_s"]["cold-site_g"]) == sorted(existing["inputs"][la]["wall_s"]["cold-site_g"]) for la in LAYOUTS)

# --- outputs -------------------------------------------------------------------------------------------------------------
COLS = ["layout", "scope", "comparator", "instances", "n_P", "n_C", "n_W", "break_even", "ci_lo", "ci_hi", "note"]


def clean(row):
    return {k: fmt(BE.json_safe(row[k])) for k in COLS if k in row}


def numeric(row):
    return {k: BE.json_safe(row[k]) for k in COLS if k in row}


with open(OUT / "breakeven-T-D.csv", "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=COLS)
    wr.writeheader()
    for r in rows:
        wr.writerow(clean(r))

meta = {"seed": SEED, "n_boot": N_BOOT, "level": LEVEL, "instances": sorted(INST), "frozen_tree_head": subprocess.run(
    ["git", "-C", str(TREE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
    "functions": {"break_even_inputs": line_of(MP.break_even_inputs), "whole_cells": line_of(MP.whole_cells),
                  "report": line_of(MP.report), "bootstrap_interval": line_of(BE.bootstrap_interval),
                  "break_even": line_of(BE.break_even), "json_safe": line_of(BE.json_safe), "load_runs": line_of(SM.load_runs)},
    "layout_provision_events_served": {f"{log[i]['layout']}@{log[i]['utc']}": s for i, s in served.items()},
    "reproduction_check_all5_instances_M_cold_site_g_vs_breakeven_json": {"pass": repro_ok, "cells": repro},
    "step_A_M_walls_equal_registered_cold_site_g_inputs_value_by_value": same_m}
twin = {"meta": meta,
        "rows": [{**numeric(r), "detail": BE.json_safe(r["_detail"]), "excluded": r["_excluded"]} for r in rows],
        "sensitivity_layout_scope_P_only_events_that_served_a_run_on_these_instances":
            [{**numeric(r), "detail": BE.json_safe(r["_detail"])} for r in sens]}
(OUT / "breakeven-T-D.json").write_text(json.dumps(twin, indent=1) + "\n")

sens_diff = [f"{a['layout']}/{a['scope']}/{a['comparator']}" for a, b in zip(
    [r for r in rows if r["scope"] == "layout"], sens)
    if (a["break_even"], a["ci_lo"], a["ci_hi"]) != (b["break_even"], b["ci_lo"], b["ci_hi"])]

# --- README ---------------------------------------------------------------------------------------------------------------
files = [MIRROR / "mplus_log.jsonl", MIRROR / "breakeven.json"] + sorted(MIRROR.glob("runs/*/run.json")) \
    + sorted(STEPA.glob("runs/*/run.json")) + [TREE / "icsa/scripted/breakeven.py", TREE / "icsa/scripted/mplus.py",
                                              TREE / "icsa/scripted/summarize.py", OUT / "compute.py"]
used_a = [r for r in aruns if r["instance_id"] in INST and r["option"] in COMPARATORS]
t_a = sorted(r["exec_started_utc"] for r in used_a)
t_m = sorted(r["exec_started_utc"] for r in mruns if r["instance_id"] in INST and r["extra"].get("variant") == "mplus")
fn = meta["functions"]
txt = f"""M+ break-even against options T and D, with M as the like-for-like reference (written {datetime.datetime.now(datetime.UTC):%Y-%m-%d %H:%MZ})

FILES
  breakeven-T-D.csv   one row per layout (S1, S2) x scope (required, layout) x comparator (T, D, M): 12 rows
  breakeven-T-D.json  the same rows plus the full bootstrap record per row (means, share of draws with no break-even,
                      excluded counts), the layout-P sensitivity, and the reproduction check
  compute.py          the script that made both (run with the frozen tree's venv and PYTHONPATH=<tree>)
  "no break-even" in the table means C <= W at the point estimate (or, in a CI bound, at that quantile of the draws).

CAVEATS
1. Added after seeing the data; descriptive; not in the registered M+ table (which compares M only).
2. 3 of M+'s 5 instances (I01, I06 have no T or D record).
3. Step A ran traced, with slot tokens; M+ and cold-site_f ran untraced with the admin token.
4. Step A ran at site_g (cold-site_g); nothing T or D ran at site_f, so there is no T/D cold-site_f comparator.
5. The step-A copy on this host was matched to the report's input by M's cold-site_g sample means only, not by hash.
   Additional check, run by compute.py (not part of the caveat above): the six step-A M wall_s values on I35/I37/I48 equal the six
   cold-site_g wall_s values in the registered breakeven.json inputs, value by value: {'yes' if same_m else 'NO'}.
Further facts:
6. Layout-scope P: the 3 layout provision events per layout carry no instance (instance is None) and each served 1-2 instances'
   runs, so P cannot be restricted by instance. The table uses all 3 per layout (n_P = 3), as the registered table does. Required-scope
   P is restricted to I35/I37/I48 by the event's instance. Sensitivity (breakeven-T-D.json, key sensitivity_*): layout-scope P kept
   only from events that served at least one layout-scope run on these 3 instances. The events' served instances are in meta.
   Cells where the sensitivity differs from the table in break_even, ci_lo or ci_hi: {', '.join(sens_diff) or 'none'}; its n_P per layout is in the JSON.
7. Step A runs used here started between {t_a[0]} and {t_a[-1]} (3 Nov); the M+ runs used here started between {t_m[0]} and {t_m[-1]} (6 Nov). They were not interleaved.
8. Comparator T is option "T" only; the step-A "T-unpaginated" records (same instances, n=3 per layout) are not used.
9. Each quantity has n=3 values per cell; the bootstrap interval resamples only those 3.

METHOD (frozen tree {TREE}, git head {meta['frozen_tree_head']}, clean apart from untracked .claude/)
  Functions reused unchanged: break_even_inputs {fn['break_even_inputs']} (builds P, W and the cold-site_g C per layout; uses whole_cells {fn['whole_cells']}
  and drops runs with ok false); bootstrap_interval {fn['bootstrap_interval']} (calls break_even {fn['break_even']}); json_safe {fn['json_safe']};
  load_runs {fn['load_runs']}. The loop over layout, scope and variant is report() {fn['report']}, reproduced for the cold-site_g variant only, because report()
  writes into its results directory.
  Seed {SEED}: the default of report()'s seed argument, equal to the seed in the registered breakeven.json. n_boot {N_BOOT} and level {LEVEL}: the
  defaults of bootstrap_interval (report() passes only the seed).
  Inputs are filtered before the calls: M+ runs and required-scope provision events to instances {INST_STR}; the layout-scope events are kept (caveat 6).
  C: the step-A records of the comparator's option on those instances, passed as site_g_runs with option relabelled "M" in copies (break_even_inputs
  reads only option M there; it is the cold-site_g column). For comparator M no relabel happens: like-for-like reference.
  Checks the script ran (it stops on failure): n_P = n_C = n_W = 3 in every row; P, C and W re-derived by another route (log events, run_key globs)
  and equal as sorted lists; reported means equal the means of those lists; reproduction: with all 5 M+ instances and step-A M, the four
  */cold-site_g entries of the registered breakeven.json are reproduced exactly (every field): {'PASS' if repro_ok else 'FAIL'}.
  Not covered by the reproduction check: T and D extraction (the registered M+ report never read T or D). They are covered only by the n and
  re-derivation assertions above.

INPUTS (read-only; sha256  path)
"""
txt += "\n".join(f"  {sha(p)}  {p}" for p in files) + "\n"
(OUT / "README.txt").write_text(txt)
print("rows", len(rows), "repro", repro_ok, "same_m", same_m)
