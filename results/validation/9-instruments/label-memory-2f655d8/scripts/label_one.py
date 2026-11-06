"""label_run on one run directory, its stages timed apart. The call is the campaign's; prints peak memory after each stage.
usage: label_one.py OPTION TRACE OUTPUT PLATFORM INSTANCE [--code FILE] [--root DIR]... [--json FILE] [--s1dir s1z] """
import argparse, hashlib, json, resource, sys, time
from pathlib import Path
t0 = time.time(); T = [t0]
def rss():
    for l in open("/proc/self/status"):
        if l.startswith("VmRSS"): return int(l.split()[1]) / 2**20
def stage(name):
    now = time.time()
    print(f"STAGE {name}: {now - T[-1]:.1f} s, rss {rss():.2f} GiB, peak so far {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20:.2f} GiB", flush=True)
    T.append(now)
ap = argparse.ArgumentParser()
for a in ("option", "trace", "output", "platform", "instance"): ap.add_argument(a)
ap.add_argument("--code"); ap.add_argument("--root", action="append", default=[]); ap.add_argument("--json"); ap.add_argument("--layout", default="S1"); ap.add_argument("--mark")
a = ap.parse_args()
from icsa import grid
from icsa.instruments.labeller import code_cells_of, label_run
from icsa.instances import load as L
stage("imports")
from icsa.instruments.fullindex import load_full_index
idx = load_full_index(); stage("load_full_index")
m = L.load_instances(); rec = next(r for r in m["instances"] if r["instance"]["instance_id"] == a.instance)
masks = L.load_sea_masks(L.DATA / m["sea_masks"]["file"], m["sea_masks"]["sha256"])
req = L.required_extent(rec, masks[rec["instance"]["region_id"]]); stage("required_extent")
print("required: baseline days", req.baseline.days.size, "target days", req.target.days.size, "box", req.baseline.box, flush=True)
code = None
if a.code:
    code = code_cells_of(a.code) if not a.code.endswith(".py") else Path(a.code).read_text()
lab = label_run(a.option, Path(a.trace), Path(a.output), idx, req, platform_dir=Path(a.platform), local_roots=[Path(r) for r in a.root],
                dir_sizes={"s1z": grid.NDAYS} if a.layout == "S1" else None, code_text=code)
stage("label_run")
def dg(pe):
    if pe is None: return None
    h = hashlib.sha256()
    for e in (pe.baseline, pe.target):
        h.update(e.days.tobytes()); h.update(e.mask.tobytes())
    return {"sha": h.hexdigest()[:16], "units_b": int(e_c(pe.baseline)), "units_t": int(e_c(pe.target))}
def e_c(e): return e.mask.sum()
def rx(r):
    if r is None: return None
    return {"ext": dg(r.extent), "files": r.files, "bytes_total": r.bytes_total, "bytes_data": r.bytes_data, "unmapped": sum(r.unmapped.values()), "n_unmapped": len(r.unmapped), "beyond": r.beyond, "beyond_days": len(r.beyond_days), "beyond_days_sha": hashlib.sha256(json.dumps(r.beyond_days).encode()).hexdigest()[:16], "source": r.source}
cc = lab.analysis.flags["cross_check"]
out = {"label": lab.label.value, "reasons": lab.reasons, "analysed": dg(lab.analysed), "loaded": dg(lab.analysis.loaded), "fetched": rx(lab.fetched), "delivered": rx(lab.delivered), "read": rx(lab.read), "observed": lab.observed,
       "listing": None if lab.listing is None else {k: v.to_json() for k, v in lab.listing.items()},
       "cross_check": {k: cc[k] for k in ("source", "unknown_file_ids", "listing_disagrees", "decoded_not_delivered", "delivered_not_decoded", "decoded_not_delivered_items", "delivered_not_decoded_items")},
       "trace_mib": round(sum(p.stat().st_size for p in Path(a.trace).iterdir() if p.is_file()) / 2**20, 2)}
s = json.dumps(out, indent=None, sort_keys=True, default=str)
print("RESULT", s, flush=True)
if a.json: Path(a.json).write_text(s)
print(f"TOTAL wall {time.time() - t0:.1f} s, peak {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20:.2f} GiB", flush=True)
