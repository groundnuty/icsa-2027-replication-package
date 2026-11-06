"""The cause inputs (read_beyond_days, delivered_not_decoded, decoded_not_delivered) through the real label_run, on real tracer streams and real byte logs,
at this checkout. Run at two heads and compare the output files. usage: cause_inputs.py MODE OUT
  stub:  whole real logs with to_units stubbed (so the old code fits): the cause inputs of the code around it
  real:  whole real logs, real to_units (the fixed code only)
  slice: the first content lines of each log, real to_units (both heads fit): extents and cause inputs together"""
import dataclasses, datetime as dt, hashlib, json, sys, tempfile
from pathlib import Path
import numpy as np
from icsa import grid
from icsa.extent import Extent, PartedExtent
from icsa.instruments import labeller as LB, readext as R, validate as V, confirm as C
from icsa.instruments.fullindex import load_full_index
from icsa.instruments.layout import _merge
mode, out_path = sys.argv[1:3]
B = Path("/mnt/volume2/icsa-2027/scratch-9p"); TR = B / "traced"; OR = B / "task1/runs"
idx = load_full_index(); p2id = {v: k for k, v in idx.ids.items()}
data = C.real_world("I01")
def s1(d): return f"s1z/sst_{grid.day_date(d):%Y%m%d}.nc"
S2 = "s2z/sst_s2.nc"
SLICE = {"S1": 30, "S2": 6}
orig = R.to_units
def stub(reads, index, box, base, tgt, *, path_map=None):
    e = Extent.empty(box); return R.ReadExtent(PartedExtent(e, e), 0, 0, 0, {}, 0, [])
if mode == "stub": R.to_units = stub
def gate(p): return [json.loads(l) for l in open(p) if l.strip()]
def cut(lines, n):
    """the first n content lines, and everything else"""
    out, k = [], 0
    for r in lines:
        if r.get("tag") == "content":
            k += 1
            if k > n: continue
        out.append(r)
    return out
def dg(pe):
    h = hashlib.sha256()
    for e in (pe.baseline, pe.target): h.update(e.days.tobytes()); h.update(e.mask.tobytes())
    return {"sha": h.hexdigest()[:16], "units": [int(pe.baseline.mask.sum()), int(pe.target.mask.sum())]}
def rx(r):
    return None if r is None else {"ext": dg(r.extent), "files": r.files, "bytes_total": r.bytes_total, "bytes_data": r.bytes_data, "beyond": r.beyond, "beyond_days": r.beyond_days, "unmapped": r.unmapped}
def label(opt, lay, scen, lines, req):
    d = TR / opt / "runs" / f"{opt}__{lay}__{scen}"
    with tempfile.TemporaryDirectory(dir=B) as t:
        t = Path(t); (t / "gate_requests.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
        return LB.label_run(opt, d / "trace", d / "output", idx, req, platform_dir=t, dir_sizes={"s1z": grid.NDAYS} if lay == "S1" else None, code_text=(d / "agent.py").read_text())
def fields(lab):
    cc = lab.analysis.flags["cross_check"]
    o = {"label": lab.label.value, "reasons": lab.reasons, "read_beyond_days": lab.read.beyond_days, "read_beyond_units": lab.read.beyond, "read": dg(lab.read.extent),
         "decoded_not_delivered": cc["decoded_not_delivered"], "dnd_items": cc["decoded_not_delivered_items"], "delivered_not_decoded": cc["delivered_not_decoded"], "ndd_items": cc["delivered_not_decoded_items"],
         "examples": cc["examples"], "listing_disagrees": cc["listing_disagrees"], "unknown_ids": cc["unknown_file_ids"], "source": cc["source"]}
    if mode != "stub": o.update(fetched=rx(lab.fetched), delivered=rx(lab.delivered))
    return o
def exp_of(opt, lay, scen):
    k, sc = C.scenario(scen); return V.expected(sc, opt, lay, data), V.required_of(data, V.expected(sc, opt, lay, data))
def chunks(ranges, whole, fl, trim):
    """chunks wholly delivered: by hand, a loop over merged runs, not crosscheck's code"""
    runs = sorted(ranges) + ([(0, fl.size)] if whole else [])
    merged = []
    for a, b in sorted(runs):
        if merged and a <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b)
        else: merged.append([a, b])
    got = set()
    for t, off, size in zip(fl.chunks[:, 0].tolist(), fl.chunks[:, 3].tolist(), fl.chunks[:, 4].tolist()):
        if any(a <= off and off + size <= b - (0 if whole else trim) for a, b in merged): got.add(t)
    return got
def gate_ranges(lines):
    out, whole = [], False
    for r in lines:
        if r.get("tag") == "content" and r.get("status") == 206:
            a = int(r["range"].split("=")[1].split("-")[0]); out.append((a, a + int(r["bytes"])))
        elif r.get("tag") == "content" and r.get("status") == 200 and r.get("method") != "HEAD": whole = True
    return out, whole
res, checks = {}, []
def check(name, cond, detail=""):
    checks.append((name, bool(cond), detail)); print(("OK  " if cond else "FAIL"), name, str(detail)[:160], flush=True)
oracle = {k: gate(OR / f"I01__{k}__qwen__s1" / "gate_requests.jsonl") for k in ("T__S1", "D__S1", "T__S2", "D__S2")} if (OR / "I01__T__S2__qwen__s1").is_dir() else None
assert oracle, "copy I01's oracle runs first"
for opt in ("T", "D"):
    # S1, a file-level skip, the real gate log from site_g: read everything, decoded all but the skip
    e, req = exp_of(opt, "S1", "skip")
    skip = sorted(int(d) for d in e["skip"])
    lines = oracle[f"{opt}__S1"]
    if mode == "slice": lines = cut(lines, SLICE["S1"])
    name = f"{opt}-S1-skip-oracle-gate"
    lab = label(opt, "S1", "skip", lines, req); res[name] = fields(lab)
    print(name, {k: res[name][k] for k in ("label", "dnd_items", "ndd_items")}, "beyond", len(res[name]["read_beyond_days"]), "skip", len(skip), flush=True)
    if mode != "slice":
        check(f"{name}: omitting, on skipped days", lab.label.value == "omitting")
        check(f"{name}: every skipped day is delivered, not decoded", res[name]["ndd_items"] == len(skip) and res[name]["delivered_not_decoded"] is True and set(res[name]["examples"]["delivered_not_decoded"]) <= {s1(d) for d in skip}, res[name]["ndd_items"])
        check(f"{name}: nothing decoded went undelivered", res[name]["dnd_items"] == 0 and res[name]["decoded_not_delivered"] is False)
    # the same with a planted skip and a planted extra read in the log
    drop = sorted(set(int(d) for d in req.baseline.days[3::400]) - set(skip))[:3]; assert len(drop) == 3
    extra = grid.day_index(dt.date(2015, 7, 4))
    drop_ids = {p2id[s1(d)] for d in drop}
    planted = [r for r in lines if not (r.get("tag") == "content" and any(i in r.get("path", "") for i in drop_ids))]
    tmpl = next(r for r in lines if r.get("tag") == "content")
    planted.append(dict(tmpl, path=tmpl["path"].replace(tmpl["path"].split("/")[-2], p2id[s1(extra)]), bytes=int(idx[s1(extra)].size), **({"range": f"bytes=0-{int(idx[s1(extra)].size) - 1}"} if tmpl.get("status") == 206 else {})))
    name = f"{opt}-S1-skip-planted"
    lab = label(opt, "S1", "skip", planted, req); res[name] = fields(lab)
    if mode != "slice":
        check(f"{name}: the dropped files are decoded, not delivered", set(res[name]["examples"]["decoded_not_delivered"]) == {s1(d) for d in drop} and res[name]["dnd_items"] == len(drop), res[name]["examples"]["decoded_not_delivered"])
        check(f"{name}: the extra file is delivered, not decoded", s1(extra) in res[name]["examples"]["delivered_not_decoded"] and res[name]["ndd_items"] == len(skip) + 1, res[name]["ndd_items"])
        if opt == "T": check(f"{name}: T's fetch outside the required days is read_beyond_days", res[name]["read_beyond_days"] == [extra], res[name]["read_beyond_days"])
    # reads more than the method needs, its own gate log: read_beyond_days from the ledger
    name = f"{opt}-S1-whole-baseline-own-gate"
    e, req2 = exp_of(opt, "S1", "complete_whole_baseline")
    d = TR / opt / "runs" / f"{opt}__S1__complete_whole_baseline"
    lines = gate(d / "platform" / "gate_requests.jsonl")
    if mode == "slice": lines = cut(lines, SLICE["S1"])
    lab = label(opt, "S1", "complete_whole_baseline", lines, req2); res[name] = fields(lab)
    want = sorted(set(int(x) for x in e["loaded_days"]) - set(int(x) for x in req2.baseline.days) - set(int(x) for x in req2.target.days)) if "loaded_days" in e else None
    print(name, "beyond", len(res[name]["read_beyond_days"]), "want", None if want is None else len(want), flush=True)
    check(f"{name}: read_beyond_days non-empty, from the ledger", len(res[name]["read_beyond_days"]) > 0, len(res[name]["read_beyond_days"]))
    check(f"{name}: read_beyond_days are the days the script read outside the requirement", res[name]["read_beyond_days"] == [int(x) for x in e["beyond_days"]] or mode == "slice", (len(res[name]["read_beyond_days"]), len(e["beyond_days"])))
    # S2, chunk level; T's real gate log from site_g reads in 5 MiB blocks, so coverage stops at chunk edges inside each read
    e, req = exp_of(opt, "S2", "skip")
    lines = oracle[f"{opt}__S2"]
    if mode == "slice" and opt == "T": lines = cut(lines, SLICE["S2"])
    if mode == "slice" and opt == "D": continue         # one whole file: the old code cannot hold it
    name = f"{opt}-S2-skip-oracle-gate"
    lab = label(opt, "S2", "skip", lines, req); res[name] = fields(lab)
    fl = idx[S2]; rng, whole = gate_ranges(lines)
    decoded = {t for t in (int(x) for x in e["loaded_days"])}
    dnd = sorted(decoded - chunks(rng, whole, fl, 0))
    ndd = [] if opt == "D" else sorted(chunks(rng, whole, fl, 5 * 2**20 + 8) - decoded)
    print(name, {k: res[name][k] for k in ("label", "dnd_items", "ndd_items")}, "by hand", len(dnd), len(ndd), "ranges", len(rng), "whole", whole, flush=True)
    check(f"{name}: decoded_not_delivered as worked out by hand", res[name]["dnd_items"] == len(dnd) and res[name]["examples"]["decoded_not_delivered"] == [f"{S2}#{t}" for t in dnd[:50]], (res[name]["dnd_items"], len(dnd)))
    check(f"{name}: delivered_not_decoded as worked out by hand, read-ahead trimmed", res[name]["ndd_items"] == len(ndd) and res[name]["examples"]["delivered_not_decoded"] == [f"{S2}#{t}" for t in ndd[:50]], (res[name]["ndd_items"], len(ndd)))
    if opt == "T":
        ends = sorted({x for r in rng for x in r}); offs = set(fl.chunks[:, 3].tolist()) | set((fl.chunks[:, 3] + fl.chunks[:, 4]).tolist())
        res[name]["read_edges_inside_a_chunk"] = sum(x not in offs for x in ends)
        res[name]["read_sizes_mib"] = sorted({round((b - a) / 2**20, 2) for a, b in rng})[-3:]
        print(name, "read edges inside a chunk", res[name]["read_edges_inside_a_chunk"], "of", len(ends), "largest reads MiB", res[name]["read_sizes_mib"], flush=True)
        check(f"{name}: reads stop inside chunks, so coverage at chunk edges is exercised", res[name]["read_edges_inside_a_chunk"] > 0)
        # a planted skip in S2: three of the real ranges gone
        cont = [k for k, r in enumerate(lines) if r.get("tag") == "content"]
        gone = {cont[1], cont[len(cont) // 2], cont[-2]}
        planted = [r for k, r in enumerate(lines) if k not in gone]
        rng2, _ = gate_ranges(planted)
        name2 = f"{opt}-S2-skip-planted"
        lab = label(opt, "S2", "skip", planted, req); res[name2] = fields(lab)
        dnd2, ndd2 = sorted(decoded - chunks(rng2, False, fl, 0)), sorted(chunks(rng2, False, fl, 5 * 2**20 + 8) - decoded)
        print(name2, {k: res[name2][k] for k in ("dnd_items", "ndd_items")}, "by hand", len(dnd2), len(ndd2), flush=True)
        if mode != "slice":
            check(f"{name2}: a real range gone: decoded_not_delivered non-empty", res[name2]["dnd_items"] > 0)
        check(f"{name2}: decoded_not_delivered as worked out by hand", res[name2]["dnd_items"] == len(dnd2) and res[name2]["examples"]["decoded_not_delivered"] == [f"{S2}#{t}" for t in dnd2[:50]], (res[name2]["dnd_items"], len(dnd2)))
        check(f"{name2}: delivered_not_decoded as worked out by hand", res[name2]["ndd_items"] == len(ndd2) and res[name2]["examples"]["delivered_not_decoded"] == [f"{S2}#{t}" for t in ndd2[:50]], (res[name2]["ndd_items"], len(ndd2)))
Path(out_path).write_text(json.dumps(res, sort_keys=True, default=str, indent=0))
bad = [c for c in checks if not c[1]]
print("checks", len(checks), "failed", len(bad)); sys.exit(1 if bad else 0)
