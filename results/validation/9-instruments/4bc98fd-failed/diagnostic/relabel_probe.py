"""Diagnostic only (lane-9r, 2 Nov): relabel finished matrix cells offline, from their kept trace and output,
with the cached index as the matrix loaded it (no content hashes) and with content hashes added, to see
whether the in-memory unknowns come from the index the harness reloads. Writes nothing into the matrix."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/mnt/volume2/icsa-2027/scratch-9/snap-4bc98fd")
from icsa.instruments import validate as V
from icsa.instruments.labeller import label_run
from icsa.instruments.layout import file_sha256

W = Path("/mnt/volume2/icsa-2027/scratch-9/matrix-4bc98fd")
data = V.make_data(W / "data-method-window")
print("cached index shas:", len(data.index.shas))
cases = sys.argv[1:]
byname = {sc.name: (k, sc) for k, sc in enumerate(V.SCENARIOS)}

def lab_of(case):
    o, lay, name = case.split("__")
    k, sc = byname[name]
    wd = W / "runs" / case
    exp = V.expected(sc, o, lay, data)
    roots = [wd / "downloads"] if o == "D" else [data.root] if o in ("M", "M+") else []
    lab = label_run(o, wd / "trace", wd / "output", data.index, V.required_of(data, exp), platform_dir=wd / "platform",
                    local_roots=roots, dir_sizes={data.s1_dir: int(len(data.s1_days))},
                    code_text=(wd / "agent.py").read_text())
    want, got = V.expected_vs(exp, lab.analysis.analysed, data, "used_days")
    wl, gl = V.expected_vs(exp, lab.analysis.loaded, data, "loaded_days")
    rc = V._read_check(lab, exp, data)
    return (lab.analysis.label.value, exp["label"].value, bool(np.array_equal(want, got)), lab.analysis.reasons,
            {"loaded_exact": bool(np.array_equal(wl, gl)), "read_exact": rc.get("read_exact"),
             "read_beyond_exact": rc.get("read_beyond_exact")})

before = {c: lab_of(c) for c in cases}
files = sorted((data.root / "s1").glob("*.nc")) + [data.root / "s2" / "sst_s2.nc"]
data.index.shas = {file_sha256(p): p.relative_to(data.root).as_posix() for p in files}
print("hashed index shas:", len(data.index.shas))
for c in cases:
    print(json.dumps({"case": c, "no_shas": before[c], "with_shas": lab_of(c)}))
