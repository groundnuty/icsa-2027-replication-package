"""M's outside view on real runs: oneclient's perf log against the tracer, through the real label_run. Planted skips and extra reads, each expectation worked out by hand.
usage: m_outside.py OUT K_RUN_DIR. K_RUN_DIR is a real M run with a tracer, given from outside: K is a blind test, so its case ids are never in the repository, and what case A finds on it is printed but not written to OUT."""
import csv, datetime as dt, glob, json, re, sys, tempfile
from pathlib import Path
from icsa import grid
from icsa.instances import load as L
from icsa.instruments import labeller as LB, validate as V, confirm as C
from icsa.instruments.analyse import load_trace, _key_indices
from icsa.instruments.fullindex import load_full_index
out_path, k_run = sys.argv[1], Path(sys.argv[2])
B = Path("/mnt/volume2/icsa-2027/scratch-9p"); TR = B / "traced"; R = B / "task1/runs"
idx = load_full_index(); S2 = "s2z/sst_s2.nc"; SPACE = "/30f507e9ae7b06e4b0af93fb125b8a92chb984"
man = L.load_instances(); masks = L.load_sea_masks(L.DATA / man["sea_masks"]["file"], man["sea_masks"]["sha256"])
def required(i):
    rec = next(r for r in man["instances"] if r["instance"]["instance_id"] == i); return L.required_extent(rec, masks[rec["instance"]["region_id"]])
data = C.real_world("I01")
HEAD = "Time,File,Class,Operation,Offset,Size,Duration [us]\n"
def row(rel, a, n, cls="FsLogic", op="read"): return f"23:24:31.593187,{SPACE}/{rel},{cls},{op},{a},{n},19151\n"
res, checks = {}, []
def check(name, cond, detail=""):
    checks.append((name, bool(cond))); print(("OK  " if cond else "FAIL"), name, str(detail)[:170], flush=True)
def label(opt, run, code, req, csv_text, lay):
    with tempfile.TemporaryDirectory(dir=B) as t:
        t = Path(t)
        if csv_text is not None:
            (t / "oneclient_perf").mkdir(); (t / "oneclient_perf" / "read_write_perf-1.csv").write_text(csv_text)
        lab = LB.label_run(opt, run / "trace", run / "output", idx, req, platform_dir=t, dir_sizes=None, code_text=code)
    cc = lab.analysis.flags["cross_check"]
    return lab, {"label": lab.label.value, "reasons": lab.reasons, "source": cc["source"], "dnd": cc["decoded_not_delivered"], "dnd_items": cc["decoded_not_delivered_items"], "ndd": cc["delivered_not_decoded"], "ndd_items": cc["delivered_not_decoded_items"], "examples": cc["examples"],
                 "read_beyond_days": None if lab.read is None else lab.read.beyond_days}
def decoded_files(run):
    """the files the ledger names, from the tracer's own streams, by hand"""
    tr = load_trace(run / "trace")
    return {tr.files[r["pid"]][r["fid"]].rsplit("/", 1)[-1] for r in tr.ledger}
def s1(name): return f"s1z/{name}"
def merged_chunks(rows, trim):
    fl = idx[S2]; rows = sorted(rows); m = []
    for a, b in rows:
        if m and a <= m[-1][1]: m[-1][1] = max(m[-1][1], b)
        else: m.append([a, b])
    return {t for t, off, size in zip(fl.chunks[:, 0].tolist(), fl.chunks[:, 3].tolist(), fl.chunks[:, 4].tolist()) if any(a <= off and off + size <= b - trim for a, b in m)}
MIB = 2**20

# ---- A: a real M run on S1, its own files (the real sandbox, the real tracer; a plain directory in place of oneclient, so it has no perf log of its own)
run = k_run; rec = json.loads((run / "run_record.json").read_text()); req = required(rec["run"]["instance_id"]); code = LB.code_cells_of(run / "cells" / "cells.jsonl")
names = sorted(decoded_files(run))
size = lambda n: int(idx[s1(n)].size)
full = HEAD + "".join(row(s1(n), 0, size(n)) for n in names)
_, none = label("M", run, code, req, None, "S1"); res["A none"] = none
check("A: no perf log: the fields are None, not agreement", none["source"] is None and none["dnd"] is None and none["ndd"] is None)
_, base = label("M", run, code, req, full, "S1"); res["A own"] = base
check("A: a log of exactly what was decoded: observed, both False", base["source"] == "oneclient_perf" and base["dnd"] is False and base["ndd"] is False and base["dnd_items"] == base["ndd_items"] == 0, base["source"])
check("A: an omitting run", base["label"] == "omitting" and base["label"] == none["label"] and base["reasons"] == none["reasons"], base["reasons"])
drop = [names[100], names[700], names[1300]]
extra = [n for n in (f"sst_{grid.day_date(d):%Y%m%d}.nc" for d in range(grid.NDAYS)) if n not in set(names)][:2]
planted = HEAD + "".join(row(s1(n), 0, size(n)) for n in names if n not in drop) + "".join(row(s1(n), 0, size(n)) for n in extra)
_, p = label("M", run, code, req, planted, "S1"); res["A planted"] = p
check("A: planted skip: exactly those files are decoded, not delivered", p["dnd"] is True and p["examples"]["decoded_not_delivered"] == sorted(s1(n) for n in drop) and p["dnd_items"] == 3, p["examples"]["decoded_not_delivered"])
check("A: planted extra read: exactly those files are delivered, not decoded", p["ndd"] is True and p["examples"]["delivered_not_decoded"] == sorted(s1(n) for n in extra) and p["ndd_items"] == 2, p["examples"]["delivered_not_decoded"])
check("A: neither touches the label", p["label"] == none["label"] and p["reasons"] == none["reasons"])
cache = full + row(s1(extra[0]), 0, size(extra[0]), "ReadCache", "read") + row(s1(extra[1]), 0, size(extra[1]), "ReadCache", "prefetch")
_, p = label("M", run, code, req, cache, "S1"); res["A readcache"] = p
check("A: oneclient's read cache alone is not a delivery", p["ndd"] is False and p["ndd_items"] == 0)

# ---- B: a real M run on S2 with the tracer on real files: chunks, with the kernel's read-ahead trimmed
run = TR / "M/runs/M__S2__skip"; code = (run / "agent.py").read_text(); e = V.expected(C.scenario("skip")[1], "M", "S2", data); req = V.required_of(data, e)
decoded = sorted(int(x) for x in e["loaded_days"]); fl = idx[S2]; at = {int(t): (int(o), int(n)) for t, o, n in zip(fl.chunks[:, 0], fl.chunks[:, 3], fl.chunks[:, 4])}
print("B: S2 decoded chunks", len(decoded))
exact = [(at[t][0], at[t][0] + at[t][1]) for t in decoded]
base_csv = HEAD + "".join(row(S2, a, b - a) for a, b in exact)
_, base = label("M", run, code, req, base_csv, "S2"); res["B own"] = base
check("B: a log of exactly what was decoded: both False", base["dnd"] is False and base["ndd"] is False and base["source"] == "oneclient_perf", (base["dnd_items"], base["ndd_items"]))
drop = [decoded[50], decoded[900]]
far = 10000                                                         # a day no required period holds
lone, trailed = far, far + 100
assert not {lone, trailed} & set(decoded)
rows = [r for r, t in zip(exact, decoded) if t not in drop] + [(at[lone][0], at[lone][0] + at[lone][1])] + [(at[trailed][0], at[trailed][0] + at[trailed][1] + 2 * MIB)]
csv_text = HEAD + "".join(row(S2, a, b - a) for a, b in rows)
_, p = label("M", run, code, req, csv_text, "S2"); res["B planted"] = p
want_ndd = sorted(merged_chunks(rows, MIB) - set(decoded))
check("B: planted skip: exactly those chunks", p["dnd"] is True and p["examples"]["decoded_not_delivered"] == [f"{S2}#{t}" for t in drop], p["examples"]["decoded_not_delivered"])
check("B: planted extra chunk and what it pulled in: by hand", p["ndd"] is True and p["examples"]["delivered_not_decoded"] == [f"{S2}#{t}" for t in want_ndd] and trailed in want_ndd, (p["examples"]["delivered_not_decoded"][:6], len(want_ndd)))
check("B: a lone chunk with nothing after it is trimmed as read-ahead", lone not in want_ndd and f"{S2}#{lone}" not in p["examples"]["delivered_not_decoded"])

# ---- C and D: real oneclient perf logs from site_g, whose runs skipped real files and chunks (calibration, I01), against the tracer's decoded set
def real_csv(tag): return next(iter(glob.glob(str(R / "perf-s1m" / tag / "*.csv"))))
def fslogic(path):
    with open(path, newline="") as fh: return [r for r in csv.DictReader(fh) if r["Class"] == "FsLogic" and r["Operation"] == "read"]
path = real_csv("s11cal-3496e216-0001-whole_file_skip.S1.M.cold.r2"); rows = fslogic(path); text = Path(path).read_text()
delivered = {r["File"].rsplit("/", 1)[-1] for r in rows}; print("C: real S1 perf log: files delivered", len(delivered))
for scen in ("complete", "skip"):
    run = TR / f"M/runs/M__S1__{scen}"; e = V.expected(C.scenario(scen)[1], "M", "S1", data); req = V.required_of(data, e)
    decoded = {f"sst_{grid.day_date(int(d)):%Y%m%d}.nc" for d in e["loaded_days"]}
    assert decoded == decoded_files(run), "the scenario and the tracer disagree on what was decoded"
    _, p = label("M", run, (run / "agent.py").read_text(), req, text, "S1"); res[f"C {scen}"] = p
    dnd, ndd = sorted(s1(n) for n in decoded - delivered), sorted(s1(n) for n in delivered - decoded)
    check(f"C {scen}: real log, decoded not delivered, by hand", p["dnd_items"] == len(dnd) and p["examples"]["decoded_not_delivered"] == dnd[:50] and p["dnd"] is bool(dnd), (p["dnd_items"], len(dnd)))
    check(f"C {scen}: real log, delivered not decoded, by hand", p["ndd_items"] == len(ndd) and p["examples"]["delivered_not_decoded"] == ndd[:50] and p["ndd"] is (bool(ndd) and p["label"] == "omitting"), (p["ndd_items"], len(ndd), p["ndd"], p["label"]))
path = real_csv("s11cal-3496e216-0004-chunk_range_skip.S2.M.prefetch_on.r0"); rows = [(int(r["Offset"]), int(r["Offset"]) + int(r["Size"])) for r in fslogic(path)]; text = Path(path).read_text()
for scen in ("complete", "skip"):
    run = TR / f"M/runs/M__S2__{scen}"; e = V.expected(C.scenario(scen)[1], "M", "S2", data); req = V.required_of(data, e)
    decoded = {int(d) for d in e["loaded_days"]}
    _, p = label("M", run, (run / "agent.py").read_text(), req, text, "S2"); res[f"D {scen}"] = p
    dnd, ndd = sorted(decoded - merged_chunks(rows, 0)), sorted(merged_chunks(rows, MIB) - decoded)
    print(f"D {scen}: decoded {len(decoded)}, delivered chunks {len(merged_chunks(rows, 0))}, label {p['label']}, dnd {p['dnd_items']}, ndd {p['ndd_items']}", flush=True)
    check(f"D {scen}: real log, decoded not delivered, by hand", p["dnd_items"] == len(dnd) and p["examples"]["decoded_not_delivered"] == [f"{S2}#{t}" for t in dnd[:50]], (p["dnd_items"], len(dnd)))
    check(f"D {scen}: real log, delivered not decoded, by hand", p["ndd_items"] == len(ndd) and p["examples"]["delivered_not_decoded"] == [f"{S2}#{t}" for t in ndd[:50]], (p["ndd_items"], len(ndd)))
Path(out_path).write_text(json.dumps({k: v for k, v in res.items() if not k.startswith("A ")}, sort_keys=True, default=str, indent=0))
bad = [c for c in checks if not c[1]]
print("checks", len(checks), "failed", len(bad)); sys.exit(1 if bad else 0)
