"""The snapshot's scored rows WITH the coding decisions applied, for H3's measure (lane-snap, #34; science 5 Nov 00:46Z: amendment 42(a), the measure's truth is the analysis label, inspection included).

    PYTHONPATH=<overlay tree> python scored_coded.py SCORED_ROWS.jsonl LABELS.jsonl COVERAGE.jsonl OUT.jsonl [CUT_STORE]      prints `scored_coded rows=N labelled=K` (counts only)
With CUT_STORE (the snapshot's `work/cut/state.sqlite`), each row's `out_of_cohort` is first recomputed against THIS cut (`snapshot.recohort`, the same step the analysis runs), so H3's measure
sees the cohort the analysis saw.

The pipeline writes `pipeline/scored_rows.jsonl` BEFORE the analysis, so it never carries `label_after_inspection`; the analysis applies the coders' decisions in memory (`icsa.analysis.inspection.apply`
then the coverage). This does the same, with the same frozen functions, and writes the rows back in the pipeline's own format (`dataclasses.asdict`, sorted keys), by rename. The measure's
`--scored` argument is a path, not part of its pin (pin_hash covers the code files only), so pointing it at this file changes no pinned byte. Nothing else is altered.
"""
import dataclasses
import json
import os
import sys

from icsa.analysis import adapter
from icsa.analysis import inspection as INS
from icsa.pipeline.postrun import dumps

scored, labels, cov, out = sys.argv[1:5]
rows = adapter.load_jsonl(scored)
if len(sys.argv) > 5:
    from snapshot import recohort
    rows, _ = recohort.apply(rows, sys.argv[5])
ins = INS.load(labels, cov)
rows2 = INS.apply(rows, ins)
by = {(r.block, r.run.key()): r for r in rows2}
tmp = out + ".tmp"
with open(tmp, "w") as fh:
    for r in rows:                                   # the pipeline's own row order
        fh.write(dumps(dataclasses.asdict(by[(r.block, r.run.key())])) + "\n")
os.replace(tmp, out)
print(f"scored_coded rows={len(rows2)} labelled={sum(1 for r in rows2 if r.label_after_inspection is not None)}")
