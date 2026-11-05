"""    python -m icsa.pipeline CAMPAIGN_ROOT --out DIR [--index-root DIR] [--data-dir DIR] [--s1-dir NAME] [--mount-root PATH] [--jobs N] [--worker-gib G]

CAMPAIGN_ROOT holds `state.sqlite` (read-only here). Writes into DIR: scored_rows.jsonl, run_records.jsonl,
run_labels.jsonl, causes.csv, cause_flags.csv, infra.json, manifest.json; ready for
`python -m icsa.analysis.run --rows DIR/scored_rows.jsonl --infra DIR/infra.json --causes DIR/causes.csv`
(plus `--inspection-labels`, the coders' decisions: `python -m icsa.analysis.inspection --decisions decisions.json --out labels.jsonl`)
and the dossier config. Exit 0 if every done run was processed, 1 if any failed (listed in the manifest), 2 on a
campaign that cannot be read."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .loadrec import PipelineError
from .postrun import run_pipeline
from .resources import Production


def main(argv=None, resources=None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.pipeline", description=__doc__.split("\n\n")[0])
    ap.add_argument("campaign_root")
    ap.add_argument("--out", required=True)
    ap.add_argument("--index-root", default=None, help="the data root holding the full layout index (default: paths.DATA_ROOT)")
    ap.add_argument("--data-dir", default=None, help="the S1 copy the reference recomputes from (default: S1_DIR under the data root)")
    ap.add_argument("--s1-dir", default="s1z", help="the S1 directory as the agent lists it (for the listing summary)")
    ap.add_argument("--mount-root", default=None, help="M, M+: the mount root, for strace-based read evidence")
    ap.add_argument("--jobs", type=int, default=1, help="instances at a time, in forked workers. Never beside a timed run on the run host")
    ap.add_argument("--worker-gib", type=int, default=8, help="each worker's address-space limit; the most a label was measured to touch is under 1 GiB")
    a = ap.parse_args(argv)
    try:
        res = resources or Production(Path(a.index_root) if a.index_root else None, a.s1_dir,
                                      Path(a.mount_root) if a.mount_root else None, Path(a.data_dir) if a.data_dir else None)
        m = run_pipeline(Path(a.campaign_root), Path(a.out), res, jobs=a.jobs, worker_gib=a.worker_gib)
    except (PipelineError, ValueError, sqlite3.Error) as e:
        print(f"icsa.pipeline: {e}", file=sys.stderr)
        return 2
    print(json.dumps(m["counts"], sort_keys=True))
    for f in m["failed"]:
        print(f"FAILED {f['block']} {f['run_key']}: {f['reason']} {f['detail']}", file=sys.stderr)
    return 1 if m["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
