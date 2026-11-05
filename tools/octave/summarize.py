"""Aggregate the per-block Octave equivalence results into one report (issue #4).

    uv run python tools/octave/summarize.py <equivalence root> <report.md> [block ...]

Copies each block's compare.json, source.json and octave.log next to the report (under
octave_blocks/<block>/), so the record survives without the volume. Never point it at octave_equivalence.md (frozen).
"""
import json
import shutil
import sys
from pathlib import Path

root, out = Path(sys.argv[1]), Path(sys.argv[2])
blocks = sys.argv[3:] or sorted(p.name for p in root.iterdir() if (p / "out" / "compare.json").exists())
keep = out.parent / "octave_blocks"
L = ["# Octave equivalence of the reference detector (issue #4)", "",
     "Each row compares one block of the authors' detectc.m, run under GNU Octave 9.2.0 (tools/octave), with ours on byte-identical input.",
     "The input sha256 is in each block's source.json.",
     "Octave's output is the only expectation.", "",
     "Columns:",
     "- *f64*: our default float64 chain;",
     "- *oct*: `precision=\"octave\"`, which emulates Octave's single-precision quantile, mean and comparison;",
     "- *octF*: Octave's own fields through our detection, which isolates the run rules.", "",
     "| block | box (lat0:lat1, lon0:lon1) | detection | sea cells | intermittent-NaN cells | m90 max abs diff f64 / oct | mclim f64 / oct | cell-days in events (Octave) | differ f64 / oct / octF | flips (max ulp) | active days differ f64 / oct | events (Octave) | events identical f64 / oct / octF |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
est_rows = []
for b in blocks:
    r = json.loads((root / b / "out" / "compare.json").read_text())
    src = json.loads((root / b / "in" / "source.json").read_text())
    f, c = r["fields"], r["cells"]
    from_ = lambda k: f"{f[k]['max_abs']:.1e}" + ("" if f[k]["nan_mismatch"] == 0 else f" ({f[k]['nan_mismatch']} NaN mismatch)")
    L.append(f"| {b} | {r['box'][0]}:{r['box'][1]}, {r['box'][2]}:{r['box'][3]} | {src['detection'][0]}..{src['detection'][1]} | "
             f"{r['cells_finite']} | {r['cells_intermittent_nan']} | {from_('m90_float64')} / {from_('m90_octave')} | "
             f"{from_('mclim_float64')} / {from_('mclim_octave')} | {r['octave']['cell_days_in_events']} | "
             f"{c['float64']['cell_days_differ']} / {c['octave_emulation']['cell_days_differ']} / {c['octave_fields']['cell_days_differ']} | "
             f"{r['flips']['exceedance_flips']} ({r['flips']['max_distance_ulp']:.2f}) | "
             f"{c['float64']['active_days_differ']} / {c['octave_emulation']['active_days_differ']} | {r['octave']['events']} | "
             f"{c['float64']['events_identical']} / {c['octave_emulation']['events_identical']} / {c['octave_fields']['events_identical']} |")
    est_rows.append((b, r["estimators_vs_octave_m90"]))
    d = keep / b
    d.mkdir(parents=True, exist_ok=True)
    for name, sub in (("compare.json", "out"), ("octave.log", "out"), ("source.json", "in"), ("meta.txt", "in")):
        if (root / b / sub / name).exists():
            shutil.copy(root / b / sub / name, d / name)
names = list(est_rows[0][1]) if est_rows else []
L += ["", "## Percentile estimator against Octave's m90 (mean abs diff, K)", "",
      "| estimator | " + " | ".join(b for b, _ in est_rows) + " |", "|---|" + "---|" * len(est_rows)]
for n in names:
    L.append(f"| {n} | " + " | ".join(f"{e[n]['mean_abs']:.2e}" for _, e in est_rows) + " |")
prov = root / "work" / "PROVENANCE"
if prov.exists():
    L += ["", "## Code provenance (work/PROVENANCE)", "", "```", prov.read_text().strip(), "```"]
    shutil.copy(prov, keep / "PROVENANCE")
out.write_text("\n".join(L) + "\n")
print(out.read_text())
