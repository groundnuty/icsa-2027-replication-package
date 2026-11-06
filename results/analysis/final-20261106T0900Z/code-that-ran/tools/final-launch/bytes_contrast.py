"""The frozen contrast_one on log2 bytes_between_sites, with Holm over the pairs of each layout (lane-snap6, 6 Nov; science #34 05:53Z and 06:01Z). A COMPOSITION of frozen functions: nothing in icsa/ is changed. Marked 'added after seeing the data'.
   python bytes_contrast.py <seal dir> --out-measured FILE --out-all FILE [--analysis out|out-coded] [--no-bootstrap]
Two sets, written to FILES only (values for science), the terminal gets counts:
 MEASURED UNITS (first; H2's rule of 5 Nov): only the units (block group, instance, layout, model) with EVERY compared option (T, D, M) measured, strictly, as in layout/bytes-measured/units.csv (status kept; the layout stage's own list, bytes_units.json);
 ALL RUNS WITH BYTES KNOWN: the primary frame as it is (runs with unknown bytes stay NaN, never 0; the paired matrix keeps the region/model pairs where both options have a value).
Rows = the seal's scored rows after recohort (as the analysis does), the primary frame (adapter.rows_to_frame), instance values of log2_bytes, then for each layout and option pair of cfg.contrasts C.contrast_one with the H4_BYTES outcome and the frozen _decorate
(Holm within outcome x layout = the pairs of one layout; an untestable pair counts as p=1 in the family)."""
import csv, os, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, os.getcwd())
from icsa.analysis import adapter, config as cfgmod, contrasts as C, secondary as S
from snapshot import recohort

seal = Path(sys.argv[1])
arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
out_m, out_a = arg("--out-measured"), arg("--out-all")
which = arg("--analysis", "out"); boot = "--no-bootstrap" not in sys.argv
cfg = cfgmod.load(None)
rows = adapter.load_jsonl(seal / which / "pipeline" / "scored_rows.jsonl")
rows, info = recohort.apply(rows, seal / "out" / "work" / "cut" / "state.sqlite")
df = adapter.rows_to_frame(rows, cfg)
main_all = df[df.option.isin(cfg.options)]
PRIMARY = set(cfg["blocks"]["primary"])
C.OUTCOME[S.H4_BYTES.name] = S.H4_BYTES       # _decorate looks the outcome up by name (a registry entry of this process only)

def contrast(main: pd.DataFrame, label: str) -> pd.DataFrame:
    inst = C.instance_values(main, S.H4_BYTES.column, defined_only=False)
    rng = np.random.default_rng(cfg["bootstrap"]["seed"])
    rr = []
    for layout in cfg.layouts:
        for a, b in cfg.contrasts:
            r, _ = C.contrast_one(inst, a, b, layout, S.H4_BYTES, cfg, boot, rng)
            rr.append(r)
    tab = C._decorate(pd.DataFrame(rr), cfg)
    tab.insert(0, "note", f"added after seeing the data (science #34 05:53Z/06:01Z); frozen contrast_one on log2 bytes_between_sites; {label}; Holm over the option pairs of one layout; not a registered test")
    tab["ratio"] = 2.0 ** tab["effect"]
    kn = main.groupby(["option", "layout"])["bytes_between_sites"].agg(known=lambda s: int(s.notna().sum()), runs="size")
    for side in ("a", "b"):
        tab[f"runs_{side}"] = [int(kn.loc[(o, l), "runs"]) if (o, l) in kn.index else 0 for o, l in zip(tab[f"option_{side}"], tab["layout"])]
        tab[f"runs_with_bytes_{side}"] = [int(kn.loc[(o, l), "known"]) if (o, l) in kn.index else 0 for o, l in zip(tab[f"option_{side}"], tab["layout"])]
    return tab

def write(tab, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True); tab.to_csv(p, index=False); os.chmod(p, 0o600)

msg = []
units_p = seal / "layout" / "bytes-measured" / "units.csv"
if out_m and units_p.is_file():
    kept = set()
    with open(units_p) as fh:
        for u in csv.DictReader(fh):
            if u["status"] == "kept":
                kept.add((u["block_group"], u["instance"], u["layout"], u["model"]))
    grp = lambda b: "primary" if b in PRIMARY else b
    keep = [(grp(b), i, l, m) in kept for b, i, l, m in zip(main_all["block"], main_all["instance_id"], main_all["layout"], main_all["model"])]
    mu = main_all[keep]
    write(contrast(mu, "MEASURED UNITS only (every compared option measured, strictly, as layout/bytes-measured/units.csv)"), out_m)
    msg.append(f"measured units: {len(kept)} kept units, {len(mu)} runs of {len(main_all)}; by option {mu.groupby('option').size().to_dict()}")
elif out_m:
    msg.append("measured-units file NOT written: layout/bytes-measured/units.csv does not exist in this seal (the layout stage did not produce it)")
if out_a:
    write(contrast(main_all, "ALL RUNS WITH BYTES KNOWN (the primary frame; unknown bytes are NaN)"), out_a)
    known = main_all.groupby("option")["bytes_between_sites"].agg(lambda s: int(s.notna().sum())).to_dict()
    msg.append(f"all runs with bytes known: {known} of {main_all.groupby('option').size().to_dict()}")
print("bytes contrast: " + " | ".join(msg) + " | written to the files (values not printed)")
