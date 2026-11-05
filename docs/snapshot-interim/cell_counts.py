"""Per cell (block x option x layout x model) run COUNTS of one snapshot, for science (#34, 4 Nov 22:31Z): the cohort's runs, finished, time-capped, exhausted, and the coding state.

    python cell_counts.py <seal dir>        # writes <seal>/cell_counts.csv (0600), first line `# snapshot final=false t=<t>`, then a header and one row per cell

Columns: block, option, layout, model, cohort_runs (every run of the cut), scored (the pipeline's scored rows), finished (the frozen parser accepted report and mask), time_capped (termination
time_cap), exhausted (status infra_exhausted in the cut: infrastructure-exhausted plus, with --no-outcome as-exhausted, the runs with no outcome at t), no_outcome_at_snapshot (the latter
alone), excluded_from_analysis, coded (a coding label applies: label_after_inspection is set), unknown_before_coding (the instrument's label is unknown), unknown_after_coding (the label that
stands after coding is unknown: the coded label where there is one, else the instrument's).
COUNTS ONLY: no label by option beyond these counts, no contrast, no rate. `coded` and the unknown counts read only the labels the snapshot itself carries (scored_rows.jsonl, which holds
`label_after_inspection` once the coders' file is given to `snapshot --inspection-labels`); the coders' decisions file is never opened here. With no coders' file, `coded` is 0 everywhere.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path


def main(seal: Path) -> int:
    cut = json.loads((seal / "out" / "work" / "cut" / "cut.json").read_text())
    store = seal / "out" / "work" / "cut" / "state.sqlite"
    cols = ("cohort_runs", "scored", "finished", "time_capped", "exhausted", "no_outcome_at_snapshot", "excluded_from_analysis", "coded_in_labels", "unknown_before_coding", "unknown_after_coding")
    ccols = ("coders_planned", "coders_dispatched", "coders_coded", "coders_valid_both")
    have_labels = (seal / "frozen" / "inspection-labels.jsonl").is_file()
    labels: dict[tuple, str] = {}
    lp = seal / "frozen" / "inspection-labels.jsonl"
    if have_labels:
        for line in lp.read_text().splitlines():
            if line.strip():
                x = json.loads(line)
                labels[(x["block"], x["run_key"])] = x["label_after_inspection"]
    coders: dict[tuple, dict] = {}
    cp = seal / "frozen" / "coders_counts.csv"
    if cp.is_file():
        with open(cp, newline="") as fh:
            for r in csv.DictReader(fh):
                coders[(r["option"], r["layout"], r["model"])] = {"coders_planned": r["planned"], "coders_dispatched": r["dispatched"], "coders_coded": r["coded"], "coders_valid_both": r["valid_both"]}
    cells: dict[tuple, dict] = defaultdict(lambda: dict.fromkeys(cols, 0))
    c = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    try:
        no_outcome = set(json.loads((c.execute("SELECT value FROM meta WHERE key='snapshot_no_outcome_runs'").fetchone() or ["[]"])[0]))
        for run_key, block, opt, lay, mod, status, excl in c.execute("SELECT run_key, block, option, layout, model, status, exclude_from_analysis FROM runs"):
            d = cells[(block, opt, lay, mod)]
            d["cohort_runs"] += 1
            d["exhausted"] += status == "infra_exhausted"
            d["no_outcome_at_snapshot"] += run_key in no_outcome
            d["excluded_from_analysis"] += bool(excl)
    finally:
        c.close()
    with open(seal / "out" / "pipeline" / "scored_rows.jsonl") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            run = r["run"]
            d = cells[(r["block"], run["option"], run["layout"], run["model"])]
            d["scored"] += 1
            d["finished"] += bool(r.get("finished"))
            d["time_capped"] += r.get("termination") == "time_cap"
            after = r.get("label_after_inspection")
            if after is None and have_labels:      # the decisions are applied by the analysis, not written into the pipeline's rows: look the run up in the labels the snapshot was given
                after = labels.get((r["block"], f"{run['instance_id']}__{run['option']}__{run['layout']}__{run['model']}__s{run['seed']}"))
            d["coded_in_labels"] += after is not None
            d["unknown_before_coding"] += r.get("label") == "unknown"
            d["unknown_after_coding"] += (after if after is not None else r.get("label")) == "unknown"
    fd = os.open(seal / "cell_counts.csv", os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", newline="") as fh:
        sj = seal / "out" / "SNAPSHOT.json"
        final = json.loads(sj.read_text()).get("final", False) if sj.is_file() else False
        fh.write(f"# snapshot final={'true' if final else 'false'} t={cut['t']}\n")
        w = csv.writer(fh)
        w.writerow(("block", "option", "layout", "model", *cols, *ccols))
        for k in sorted(cells):
            row = [int(cells[k][x]) for x in cols]
            if not have_labels:
                row[cols.index("unknown_after_coding")] = "needs_unseal"          # not computable without the coders' decisions (sealed until science unseals them): never a 0, which would read as "none unknown"
            cc = coders.get(k[1:]) if k[0] == "main" else None
            w.writerow((*k, *row, *((cc or {}).get(x, "") for x in ccols)))
    print(f"cell_counts: cells={len(cells)} file={seal / 'cell_counts.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
