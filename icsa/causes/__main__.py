"""    python -m icsa.causes code  --evidence DIR --out causes.csv      # rule coder -> block,run_key,cause,...
    python -m icsa.causes sheet --evidence DIR --out SHEETDIR        # blind sheet (+ key.csv, codebook.md)
    python -m icsa.causes kappa --key key.csv --causes causes.csv --sheet filled.csv --out kappa.csv
`DIR` is what `evidence.write_evidence` wrote."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .batch import code_runs
from .evidence import read_evidence
from .kappa import kappa_report
from .sampling import write_sheet


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.causes")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("code")
    c.add_argument("--evidence", required=True)
    c.add_argument("--out", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--evidence", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--fraction", type=float, default=0.2)
    s.add_argument("--seed", type=int, default=0)
    k = sub.add_parser("kappa")
    k.add_argument("--key", required=True)
    k.add_argument("--causes", required=True)
    k.add_argument("--sheet", required=True)
    k.add_argument("--out", required=True)
    k.add_argument("--n-boot", type=int, default=2000)
    k.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    if a.cmd in ("code", "sheet"):
        batch = code_runs(read_evidence(a.evidence))
        if a.cmd == "code":
            batch.table().to_csv(a.out, index=False)
            flags = a.out.removesuffix(".csv") + ".flags.csv"
            batch.flags_table().to_csv(flags, index=False)
            print(json.dumps({"coded": len(batch.codings), "skipped": batch.skipped_counts(),
                              "breakdowns": batch.breakdowns(),
                              "listing_evidence_incomplete": batch.listing_evidence_incomplete_count(),
                              "listing_evidence_incomplete_by_option": batch.listing_evidence_incomplete_by_option(),
                              "listing_disagrees_by_option": batch.listing_disagrees_by_option(),
                              "flags": flags}))
        else:
            print(json.dumps(write_sheet(batch, a.out, a.fraction, a.seed)))
    else:
        rep = kappa_report(pd.read_csv(a.key), pd.read_csv(a.causes), pd.read_csv(a.sheet, keep_default_na=False),
                           n_boot=a.n_boot, seed=a.seed)
        rep.to_csv(a.out, index=False)
        print(rep.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
