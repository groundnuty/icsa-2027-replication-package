"""Relabel every finished matrix cell at this checkout, from its kept trace, output and platform logs: the whole result, with
digests of every extent. Writes one JSON line per case. Run at two heads and compare. usage: relabel_all.py DATA RUNS OUT [--mark]"""
import hashlib, json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from icsa.instruments import validate as V
from icsa.instruments.labeller import label_run
data_dir, runs, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
data = V.make_data(data_dir)
assert data.index.shas, "index without hashes"
byname = {sc.name: (k, sc) for k, sc in enumerate(V.SCENARIOS)}
def dg(pe):
    if pe is None: return None
    h = hashlib.sha256()
    for e in (pe.baseline, pe.target):
        h.update(e.days.tobytes()); h.update(e.mask.tobytes())
    return h.hexdigest()
def rx(r):
    if r is None: return None
    return {"ext": dg(r.extent), "files": r.files, "bytes_total": r.bytes_total, "bytes_data": r.bytes_data, "unmapped": r.unmapped, "beyond": r.beyond, "beyond_days": r.beyond_days, "source": r.source, "downloaded_days": r.downloaded_days}
def one(case):
    o, lay, name = case.split("__")
    k, sc = byname[name]; wd = runs / case
    exp = V.expected(sc, o, lay, data)
    roots = [wd / "downloads"] if o == "D" else [data.root] if o in ("M", "M+") else []
    try:
        lab = label_run(o, wd / "trace", wd / "output", data.index, V.required_of(data, exp), platform_dir=wd / "platform", local_roots=roots,
                        dir_sizes={data.s1_dir: int(len(data.s1_days))}, code_text=(wd / "agent.py").read_text())
    except Exception as e:
        return {"case": case, "error": repr(e)}
    an = lab.analysis
    return {"case": case, "label": lab.label.value, "reasons": lab.reasons, "summary": json.loads(json.dumps(lab.summary(), sort_keys=True, default=str)),
            "analysed": dg(an.analysed), "loaded": dg(an.loaded), "analysed_upper": dg(getattr(an, "analysed_upper", None)), "bound": dg(an.bound),
            "fetched": rx(lab.fetched), "delivered": rx(lab.delivered), "read": rx(lab.read)}
if __name__ == "__main__":
    cases = sorted(p.name for p in runs.iterdir() if (p / "trace").is_dir())
    with ProcessPoolExecutor(8) as ex, open(out, "w") as fh:
        for r in ex.map(one, cases, chunksize=4):
            fh.write(json.dumps(r, sort_keys=True, default=str) + "\n")
    print("cases", len(cases), "errors", sum('"error"' in l for l in open(out)))
