"""The coders' coverage records for the analysis (amendment 19(f), rubric §5, F5).

    python -m icsa.inspection.coverage --population population.jsonl --decisions decisions.json --out records.jsonl
    python -m icsa.inspection.coverage --population population.jsonl --key key.json --work WORK --packets PACKETS --out records.jsonl

One record per inspected run, the format `analysis.adapter.apply_inspection_coverage(rows, records)` reads: `block`, `run_key`,
`both_agree_exactly`, `coverage_baseline`, `coverage_target` (and, for the reader's sake ignored, `store_run_key`, `why` and `coder_pair`).

- **The pair is the run's own** (amendment 26, `plan.py`): each packet carries the pair that coded it (`decisions.json`'s `pair`), Sol + Opus
  or Opus + Sonnet, and its record is made from THAT pair's two extractions and says which: `coder_pair` is `sol+opus` or `opus+sonnet`
  (`codex+claude` and `sonnet+claude` coders, in the decisions). A run the plan left uncoded (`not_coded`: a Sonnet subject run met by a closed
  quota gate) gets no record, is counted apart (`not_coded_r_packets`) and stays not inspected. The counts are also given `by_pair`.

- **Which runs.** Only the set R packets (set N, a pilot run with no label, is answered and never scored: no record, and the reader's
  scored row has `label None` for it): the runs the instrument left `unknown`, whose coders have both answered. A set C or K packet
  never gets one (the instrument's label stands, and the reader raises on a record for a definite label); neither does a run with
  no packet (refused, pending, unlabelled: the reader's scored row has `label None` for an unfinished run, and it refuses a record
  for one). A population row that is unlabelled or not `unknown` but has a packet is an error here, not a skipped record.
- **`run_key` is the record's key** (`ScoredRow.run.key()`), with `block`: the population row's `key` and `block`. The packet's own
  `run_key` is the store key, and is kept as `store_run_key`.
- **`both_agree_exactly`** is `decide.decomposition(...)["computable"]`: both coders' extractions identical (`compare`'s
  `extraction_sha256`) and neither leaves any part CANNOT TELL or names cells by a rule (`exact`). Otherwise the record says
  false, with the reason in `why`, and both shares are null, which is what the reader keeps.
- **The shares** are the instrument's own definition of coverage, per part: the required (day, sea cell) pairs the extraction
  covers, `1 - missing / required`, from `compare.Verdict.missing_cell_days_by_part` and `required_cell_days`. Identical
  extractions give identical counts; a difference between the coders' counts is an error.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

from . import decide
from . import plan as PL

CODERS = ("codex", "claude")          # a packet with no pair of its own (decisions made before the plan existed) is read as this pair
PARTS = ("baseline", "target")


class CoverageError(ValueError):
    """Decisions and population that cannot be turned into records the reader would accept."""


def shares(detail: dict) -> dict[str, float]:
    """Each part's coverage from one coder's `compare.Verdict.to_dict()`: 1 - missing / required, in [0, 1]."""
    req, mis = detail.get("required_cell_days"), detail.get("missing_cell_days_by_part")
    if not isinstance(req, dict) or not isinstance(mis, dict) or any(p not in req or p not in mis for p in PARTS):
        raise CoverageError("the verdict has no per-part cell-day counts: the decisions were made before compare.py gave them; "
                            "run the report's decisions again")
    out = {}
    for p in PARTS:
        r, m = req[p], mis[p]
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (r, m)) or not 0 <= m <= r or r == 0:
            raise CoverageError(f"{p}: {m} cell-days missing of {r} required is not a share")
        out[p] = 1 - m / r
    return out


def record_for(packet: dict, row: dict) -> dict:
    """The record of one decided set R packet (`report.decisions` entry) and its population row."""
    pair = tuple(packet.get("pair") or CODERS)
    if "sonnet" in pair and PL.is_sonnet_subject(packet.get("model")):
        raise CoverageError(f"{packet['run_key']}: Opus + Sonnet on a Sonnet subject run (a subject model never judges its own runs)")
    d1, d2 = (packet["coders"][c]["detail"] for c in pair)
    agree = decide.decomposition(d1, d2)
    rec = {"block": row["block"], "run_key": row["key"], "store_run_key": packet["run_key"],
           "both_agree_exactly": bool(agree["computable"]), "coverage_baseline": None, "coverage_target": None,
           "why": None if agree["computable"] else agree["why"], "coder_pair": PL.pair_name(pair) or "+".join(pair)}
    if agree["computable"]:
        a, b = shares(d1), shares(d2)
        if a != b:
            raise CoverageError(f"{packet['run_key']}: identical extractions, different cell-day counts {a} vs {b}")
        rec["coverage_baseline"], rec["coverage_target"] = a["baseline"], a["target"]
    return rec


def records(decisions: dict, population: list[dict]) -> tuple[list[dict], dict]:
    """(records, counts). `decisions`: `report.decisions`' return; `population`: the rows `population.py` wrote."""
    by_run = {r["run_key"]: r for r in population}
    out: list[dict] = []
    seen: set = set()
    pending = not_coded = 0
    for pid in sorted(decisions["packets"]):
        p = decisions["packets"][pid]
        row = by_run.get(p["run_key"])
        if p["set"] not in ("R", "C"):
            continue
        if row is None:
            raise CoverageError(f"packet {pid} is run {p['run_key']}, which is not in the population")
        if row.get("unlabelled"):
            raise CoverageError(f"run {p['run_key']} is unlabelled (no final label) but has a packet: no coverage record for it")
        if p["set"] == "C":
            continue                                    # the instrument's label stands: no record, whatever the coders said
        if row["label"] != "unknown":
            raise CoverageError(f"run {p['run_key']} is in set R but the population labels it {row['label']!r}: a record "
                                "for a definite label is refused by the reader")
        if p.get("not_coded"):
            not_coded += 1               # a Sonnet subject run the plan left uncoded: not inspected, its unknown stands
            continue
        if p["pending"]:
            pending += 1
            continue
        if not row.get("block") or not row.get("key"):
            raise CoverageError(f"run {p['run_key']}: the population row has no block and key (the reader's join)")
        rec = record_for(p, row)
        k = (rec["block"], rec["run_key"])
        if k in seen:
            raise CoverageError(f"two records for {k}")
        seen.add(k)
        out.append(rec)
    out.sort(key=lambda r: (r["block"], r["run_key"]))
    by_pair = {}
    for name in sorted({r["coder_pair"] for r in out}):
        mine = [r for r in out if r["coder_pair"] == name]
        by_pair[name] = {"records": len(mine), "both_agree_exactly": sum(r["both_agree_exactly"] for r in mine)}
    counts = {"records": len(out), "both_agree_exactly": sum(r["both_agree_exactly"] for r in out),
              "not_exact": sum(not r["both_agree_exactly"] for r in out), "pending_r_packets": pending,
              "not_coded_r_packets": not_coded, "by_pair": by_pair,
              "not_exact_by_reason": dict(sorted(collections.Counter(r["why"] for r in out if r["why"]).items()))}
    return out, counts


def write(recs: list[dict], path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in recs))
    os.replace(tmp, path)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.inspection.coverage", description=__doc__.split("\n\n")[0])
    ap.add_argument("--population", required=True, help="the rows population.py wrote (block and key give the reader's join)")
    ap.add_argument("--decisions", help="the report's decisions.json")
    ap.add_argument("--key", help="without --decisions: the queue's key file, to take the decisions from --work")
    ap.add_argument("--work", help="the coders' work directory (answers/<pid>/<coder>/final.json); with --sealed, the public one")
    ap.add_argument("--packets", help="the packet directory (<pid>.lines.json)")
    ap.add_argument("--pair-plan", help="the main block's coding plan (plan.py), so that each packet is read by its own pair")
    ap.add_argument("--sealed", help="the main block's sealed directory (needs --pair-plan and --unseal)")
    ap.add_argument("--unseal", action="store_true",
                    help="read the sealed directory. Under amendment 29(c) the SCIENCE agent alone runs snapshots and reads their tables; no lane that "
                         "runs the campaign computes a contrast. That rests on instruction, not on a lock (mode 700 guards against accidents only)")
    ap.add_argument("--c-main-per-cell", type=int, default=15)
    ap.add_argument("--out", required=True, help="records.jsonl, for icsa.analysis.run --inspection")
    a = ap.parse_args(argv)
    try:
        from .queue import read_population
        for d in (a.work, a.sealed):
            if d:
                PL.require_unsealed(d, a.unseal)
        pop = read_population(a.population)
        if a.decisions:
            decs = json.loads(Path(a.decisions).read_text())
        elif a.sealed and a.pair_plan and a.work:
            if a.key and not a.packets:
                ap.error("--key with --sealed needs --packets too: the gate's packets are read from there")
            from icsa.instances.load import load_required_extents
            from .report import decisions
            key, pair_plan, _ = PL.main_inputs(a.pair_plan, a.sealed, a.population, a.work, key_path=a.key, unseal=a.unseal,
                                               c_main_per_cell=a.c_main_per_cell)
            extents = load_required_extents()
            decs = decisions(key, a.work, lambda iid: extents[iid], a.packets or ".", pair_plan, unseal=a.unseal)
        elif a.key and a.work and a.packets:
            from icsa.instances.load import load_required_extents
            from .report import decisions
            extents = load_required_extents()
            key = json.loads(Path(a.key).read_text())
            pair_plan = PL.PairPlan.load(a.pair_plan, a.work, key) if a.pair_plan else None
            decs = decisions(key, a.work, lambda iid: extents[iid], a.packets, pair_plan, unseal=a.unseal)
        else:
            ap.error("give --decisions, or --key, --work and --packets together, or --sealed with --pair-plan and --work")
        recs, counts = records(decs, pop)
    except (CoverageError, PL.SealError, PL.PlanError, ValueError, KeyError, OSError) as e:
        print(f"icsa.inspection.coverage: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    write(recs, a.out)
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
