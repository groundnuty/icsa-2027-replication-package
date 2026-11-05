"""Regenerate the analysis tables of the fixed snapshot from the shipped inputs, and compare them with the shipped tables.

    uv run python reproduce/regenerate.py [--snapshot results/analysis] [--out build/tables] [--check]

This repeats, step by step, what the snapshot tool (`snapshot/run.py`, function `analyse`) did after its pipeline had scored the runs:

1. read the scored rows (`pipeline/scored_rows.jsonl`), the coded causes, the cause flags and the infrastructure export;
2. recompute each row's `out_of_cohort` against the snapshot's cohort cut (`snapshot/recohort.py`), from the counted start of every run
   (`inputs/counted_starts.csv`) instead of the campaign store, which is not shipped;
3. load the enforcement overhead, the fault-injection fidelity rows and H3 table, and the coders' inspection labels and coverage, as the snapshot did;
4. call the pre-registered analysis (`icsa.analysis.run.run_all`) with the default configuration;
5. put the snapshot's header line first in every table (`snapshot/stamp.py`).

With `--check`, every file under the shipped `tables/` is compared byte for byte with the regenerated one. Tables (.csv, .md) and `manifest.json` must be
identical; figures (.png) are compared too, but a different PNG is reported, not failed, as its bytes depend on the plotting library's build.
The last line reads `check: all N tables byte-identical to the shipped files` when they are. No network, no campaign store, no model call.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import filecmp
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

NONE = "none"


def _opt(path: pathlib.Path) -> pathlib.Path | None:
    return path if path.is_file() else None


def recohort(rows, starts_csv: pathlib.Path, cohort_cut: str):
    """`snapshot.recohort.apply`, with the counted starts read from a CSV (store_run_key, counted_start_utc) instead of the cut's store."""
    from snapshot.cut import utc
    starts = {}
    with open(starts_csv, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            starts[r["store_run_key"]] = r["counted_start_utc"]
    cut = utc(cohort_cut)
    out, info = [], {"rows": 0, "stamp_out_to_in": 0, "stamp_in_to_out": 0, "unchanged": 0, "no_counted_start": 0}
    for r in rows:
        ts = starts.get(f"{r.block}__{r.run.key()}")
        if ts is None:
            info["no_counted_start"] += 1
            out.append(r)
            continue
        new = utc(ts) >= cut
        if new == bool(r.out_of_cohort):
            info["unchanged"] += 1
            out.append(r)
        else:
            info["stamp_out_to_in" if not new else "stamp_in_to_out"] += 1
            out.append(dataclasses.replace(r, out_of_cohort=new))
    info["rows"] = len(out)
    return out, info


def regenerate(snap: pathlib.Path, out: pathlib.Path) -> dict:
    import pandas as pd
    from icsa.analysis import adapter, config as cfgmod, inspection as INS, overhead as OV
    from icsa.analysis.run import run_all
    from snapshot import stamp

    meta = json.loads((snap / "SNAPSHOT.json").read_text(encoding="utf-8"))
    pdir, idir = snap / "pipeline", snap / "inputs"
    inputs = json.loads((idir / "inputs.json").read_text(encoding="utf-8"))
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty: give a new directory")
    out.mkdir(parents=True, exist_ok=True)

    cfg = cfgmod.load(None)                                       # the snapshot ran with the default configuration
    ov_path = _opt(idir / "overhead.json")
    ov = OV.load(str(ov_path), cfg) if ov_path else OV.OverheadTable.absent()
    fid_path = _opt(idir / "fidelity_rows.jsonl")
    fid = adapter.load_fidelity_rows(str(fid_path)) if fid_path else []
    h3_path = _opt(idir / "h3_table.csv")
    lab_path = _opt(idir / "inspection-labels.jsonl")
    cov_path = _opt(idir / "inspection-coverage.jsonl")
    ins = INS.load(str(lab_path), str(cov_path) if cov_path else None) if lab_path else INS.InspectionInput.not_run()

    rows = adapter.load_jsonl(str(pdir / "scored_rows.jsonl"))
    info = None
    if inputs.get("recohort", True):
        rows, info = recohort(rows, idir / "counted_starts.csv", inputs["cohort_cut_utc"])
        want = inputs.get("recohort_totals")
        if want and {k: want[k] for k in info} != info:
            raise SystemExit(f"recohort gives {info}, the snapshot recorded {want}: the inputs do not match the snapshot")
    run_all(rows, out, cfg, pd.read_csv(pdir / "causes.csv"), fidelity_rows=fid,
            h3_table=pd.read_csv(h3_path) if h3_path else None,
            cause_flags=pd.read_csv(pdir / "cause_flags.csv"), infra=pdir / "infra.json", overhead=ov, inspection=ins, audit=None)
    line = stamp.header(bool(meta["final"]), meta["t"])
    stamp.stamp_tables(out, line)
    stamp.check_tables(out, line)
    return {"rows": len(rows), "recohort": info, "files": sum(1 for p in out.rglob("*") if p.is_file())}


def compare(shipped: pathlib.Path, made: pathlib.Path) -> int:
    a = {p.relative_to(shipped).as_posix() for p in shipped.rglob("*") if p.is_file()}
    b = {p.relative_to(made).as_posix() for p in made.rglob("*") if p.is_file()}
    bad, png_diff, same = [], [], 0
    for rel in sorted(a | b):
        if rel not in b:
            bad.append(f"missing from the regenerated tables: {rel}")
        elif rel not in a:
            bad.append(f"regenerated but not shipped: {rel}")
        elif filecmp.cmp(shipped / rel, made / rel, shallow=False):
            same += 1
        elif rel.endswith(".png"):
            png_diff.append(rel)
        else:
            bad.append(f"differs: {rel}")
    for line in bad:
        print(line)
    if png_diff:
        print(f"figures that differ in bytes (reported, not failed): {len(png_diff)}: {', '.join(png_diff)}")
    n_tables = sum(1 for r in a if not r.endswith(".png"))
    if bad:
        print(f"check: FAILED, {len(bad)} of {len(a | b)} files")
        return 1
    print(f"check: all {n_tables} tables byte-identical to the shipped files ({same} files identical, {len(png_diff)} figures differ in bytes)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", type=pathlib.Path, default=ROOT / "results" / "analysis")
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "build" / "tables")
    ap.add_argument("--check", action="store_true", help="compare the regenerated tables with the shipped ones")
    a = ap.parse_args(argv)
    if not (a.snapshot / "SNAPSHOT.json").is_file():
        print(f"no snapshot at {a.snapshot}: the results of the fixed snapshot are not in this copy yet (see MISSING.md)", file=sys.stderr)
        return 2
    res = regenerate(a.snapshot, a.out)
    print(f"regenerated {res['files']} files from {res['rows']} scored rows into {a.out}"
          + (f"; recohort: {res['recohort']}" if res["recohort"] else ""))
    return compare(a.snapshot / "tables", a.out) if a.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
