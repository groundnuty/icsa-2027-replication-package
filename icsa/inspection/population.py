"""The inspection population (the rows `queue.build` takes) from a campaign's own records (#76).

    python -m icsa.inspection.population --campaign-root DIR [--pipeline-out DIR] [--infra FILE]
        [--phase P] [--exclude-unbuildable] --out population.jsonl

Writes `population.jsonl` (one row per planned run that is a result or counts as unknown) and `population.excluded.jsonl` beside
it (every other run of the campaign, with a reason), and prints counts only: rows by label, by option x layout and by phase,
the unlabelled runs, excluded by reason.

Inputs, each read with the reader that owns its format:
- the campaign store `CAMPAIGN_ROOT/state.sqlite` (`pipeline.postrun.ReadOnlyStore`, read-only): the campaign's own PLAN. Every
  run of it ends in `rows` or `excluded`, none is dropped, and the store is the authority for a run's block, option, layout,
  model, seed, status and `exclude_from_analysis`;
- the pipeline's `run_labels.jsonl` (by `store_run_key`: the label, its reasons and the cross-check flags),
  `scored_rows.jsonl` (`analysis.adapter.load_jsonl`: the label the analysis reads, None when a run did not finish) and
  `infra.json` (`analysis.infra.load_export`: each analysed attempt's `run_dir`, the only place the pipeline records it).

What a row is. `run_key` is the STORE key `block__instance__option__layout__model__sN`, because a pilot run and the
main run of the same cell share the record's key (`key`, kept on the row) and `queue.assign_sets` refuses duplicates;
`block` and `key` stay for the join back to the scored rows. `phase` comes from the block (`BLOCK_PHASE`; the pagination
block's runs, T-unpaginated, are phase `pagination`, which `queue.assign_sets` treats as main: its `unknown` runs are
set R and its decided runs are sampled per option x layout); `--phase` only gives a phase to a block that has none. `label`
is the pipeline's, as written: amendment 19(a)'s routing of a loaded-not-used-only `omitting` to `unknown` is already in it, so
it is never applied here. `label_raw`, `label_reasons` and `notes` are kept as written.

The unlabelled runs (science, #76, 20:26Z and 22:28Z). Every planned run whose label is not usable is a row of its own with
`unlabelled: true` and `unlabelled_reason`: never started or still pending, infra-exhausted, a harness error not yet re-run, done
with no valid report and mask (`ScoredRow.label` is None), a pipeline output that is missing, failed or older than the store, a label
that is missing or disagrees between the files. A run re-queued after a harness error counts with its final label if the store has
it done and the pipeline has labelled it, and as unlabelled only if it is not.
- A run ended by the time cap ("K" in report-spec, which has nothing to do with set K; here `time_capped`) is `time_capped: true` with
  `label: None`: it made no claim, so part 5 takes it out of both its numerator and its denominator and reports it beside the share.
  It is told by the scored row's TERMINATION (`sr.termination == TIME_CAP`), never by `invalid_reason`, which `score_run` takes
  from the report or the mask first: a capped run with no report reads as `report_missing`.
- Any other unlabelled run is `label: "unknown"` and counts against the share (a harness or infrastructure loss included).
- In the PILOT, every unlabelled run (time-capped or not) is a set N packet: read by the coders, its answer never scored against a
  label (`queue.assign_sets`); one with nothing to build is refused into the key's `refused`. Another phase's unlabelled run is in
  no set. No unlabelled run ever gets an inspection verdict or a coverage record (`coverage.py`; the analysis' reader refuses a record
  for a label that is None). `report.py` counts them in part 5.
`instrument_label` keeps what the pipeline's `run_labels.jsonl` said: an unfinished run the instrument decided (complete or omitting)
is NOT set C, whatever the rubric's §1 says of "runs the instrument labels", because the scored row has no label for it; the summary
counts them per phase (`unlabelled_instrument_decided_by_phase`) so that the loss is visible, and a ruling to put them in C changes
the queue only.

What is excluded, with a reason: a block with no phase, a store row that names no option, a run flagged `exclude_from_analysis`
outside the calibration block (which carries the flag by design), a bad cross-check flag, and what the pipeline's files hold of runs
the store does not (the summary counts the excluded per phase: an excluded pilot run is not in part 5's denominator). A labelled run
with no recorded run directory, or whose directory lacks its transcript or code cells, stays a row, marked in `packet_problem`:
`queue.build` refuses its packet and lists it in the key's `refused`, which is where `report.py` counts a refused `unknown` pilot run as
unknown for certain. Excluding it here (`exclude_unbuildable`) also takes it out of part 5's denominator, so it is not the default.

Which of these runs the coders see stays `queue.assign_sets` (R, C, the main strata); nothing here duplicates it.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sqlite3
import sys
from pathlib import Path

from icsa.records import Termination

from .queue import LABELS, PHASES as QUEUE_PHASES, assign_sets

PHASES = tuple(p for p in QUEUE_PHASES if p != "ktest")
BLOCK_PHASE = {p: p for p in PHASES}        # each campaign block is its own phase; the queue gives each its rule
ROW_FIELDS = ("run_key", "run_dir", "instance_id", "option", "layout", "model", "seed", "phase", "label", "label_raw",
              "label_reasons", "notes", "decoded_not_delivered", "delivered_not_decoded", "block", "key", "attempt",
              "out_of_cohort", "packet_problem", "instrument_label", "unlabelled", "time_capped", "unlabelled_reason", "unlabelled_detail")
EXCLUDED_FIELDS = ("run_key", "block", "key", "phase", "instance_id", "option", "layout", "model", "seed", "reason", "detail",
                   "label")
DETAIL_CAP = 500


class PopulationError(ValueError):
    """An input that cannot be read: the whole build stops (a run that cannot be used is excluded instead)."""


def _record_key(s) -> str | None:
    from icsa.records import Layout, Option, RunId
    try:
        return RunId(s["instance_id"], Option(s["option"]), Layout(s["layout"]), s["model"], int(s["seed"])).key()
    except (ValueError, TypeError, KeyError):
        return None


def _load_store(campaign_root: Path) -> tuple[list[dict], dict[str, tuple[int, str | None]]]:
    from icsa.pipeline.loadrec import PipelineError
    from icsa.pipeline.postrun import ReadOnlyStore
    try:
        store = ReadOnlyStore(campaign_root / "state.sqlite")
    except PipelineError as e:
        raise PopulationError(f"campaign store: {e}") from e
    except sqlite3.Error as e:
        raise PopulationError(f"campaign store: {type(e).__name__}: {e}") from e
    try:
        runs = [dict(r) for r in store.q("SELECT run_key, block, instance_id, option, layout, model, seed, status,"
                                         " exclude_from_analysis FROM runs ORDER BY run_key")]
        done = {r["run_key"]: (r["attempt"], r["run_dir"])
                for r in store.q("SELECT run_key, attempt, run_dir FROM attempts WHERE state='done'")}
    except sqlite3.Error as e:
        raise PopulationError(f"campaign store: {type(e).__name__}: {e}") from e
    finally:
        store.close()
    return runs, done


def _load_labels(path: Path) -> dict[str, dict]:
    from icsa.instruments.readext import jsonl
    if not path.is_file():
        raise PopulationError(f"{path} not found")
    out: dict[str, dict] = {}
    try:
        rows = list(jsonl(path))
    except ValueError as e:
        raise PopulationError(f"{path}: {type(e).__name__}: {e}") from e
    for r in rows:
        k = r.get("store_run_key") if isinstance(r, dict) else None
        if not k:
            raise PopulationError(f"{path}: a row has no store_run_key")
        if k in out:
            raise PopulationError(f"{path}: {k} appears twice")
        out[k] = r
    return out


def _load_scored(path: Path) -> dict[tuple, object]:
    from icsa.analysis.adapter import load_jsonl
    if not path.is_file():
        raise PopulationError(f"{path} not found")
    try:
        rows = load_jsonl(path)
    except (ValueError, TypeError, KeyError) as e:
        raise PopulationError(f"{path}: {type(e).__name__}: {e}") from e
    out: dict[tuple, object] = {}
    for r in rows:
        k = (r.block, r.run.key())
        if k in out:
            raise PopulationError(f"{path}: {k} appears twice")
        out[k] = r
    return out


def _load_infra(path: Path):
    from icsa.analysis.infra import load_export
    if not path.is_file():
        raise PopulationError(f"{path} not found (the run directories are recorded only there)")
    try:
        return load_export(path)
    except (ValueError, OSError) as e:
        raise PopulationError(f"{path}: {type(e).__name__}: {e}") from e


def _load_failed(path: Path) -> dict[tuple, str]:
    """The pipeline's own list of runs it could not process, by (block, record key); the manifest is optional detail."""
    if not path.is_file():
        return {}
    try:
        m = json.loads(path.read_text())
        return {(f["block"], f["run_key"]): f"{f['reason']}: {f.get('detail', '')}" for f in m.get("failed", [])}
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise PopulationError(f"{path}: {type(e).__name__}: {e}") from e


def _packet_problem(run_dir: str) -> str | None:
    """Why `packet.read_run` cannot read this directory, by the files it needs; None when it can start."""
    d = Path(run_dir)
    if not d.is_dir():
        return "run_dir_missing"
    if not (d / "transcript.json").is_file():
        return "transcript_missing"
    c = d / "code_cells.json"
    if not c.is_file():
        return "code_cells_missing"
    try:
        cells = json.loads(c.read_text())
    except (OSError, ValueError):
        return "code_cells_unreadable"
    return None if isinstance(cells, list) and cells else "no_code_cells"


def _flag(v) -> bool | None | str:
    return v if v is None or isinstance(v, bool) else "invalid"


def rows_from_pipeline(pipeline_out_dir, *, campaign_root, phase: str | None = None, infra=None,
                       exclude_unbuildable: bool = False) -> tuple[list[dict], list[dict]]:
    """(rows, excluded): every run of the campaign store is in exactly one of them. See the module docstring.

    `phase`: the phase of a run whose block has none of its own (None: such runs are excluded).
    `infra`: the infra export (default `pipeline_out_dir/infra.json`)."""
    if phase is not None and phase not in PHASES:
        raise ValueError(f"phase {phase!r} is not one of {PHASES}")
    out, root = Path(pipeline_out_dir), Path(campaign_root)
    if not out.is_dir():
        raise PopulationError(f"pipeline output {out} not found: run `python -m icsa.pipeline CAMPAIGN_ROOT --out DIR` and pass it")
    runs, store_done = _load_store(root)
    account = _load_infra(Path(infra) if infra else out / "infra.json")
    labels = _load_labels(out / "run_labels.jsonl")
    scored = _load_scored(out / "scored_rows.jsonl")
    failed = _load_failed(out / "manifest.json")
    analysed = {(a["block"], a["key"]): a for a in account.analysed}
    exhausted = {e["run_key"]: e for e in account.exhausted}
    rows: list[dict] = []
    excluded: list[dict] = []

    def exclude(s: dict, key, why: str, detail="", *, phase_=None, label=None) -> None:
        excluded.append({"run_key": s["run_key"], "block": s["block"], "key": key, "phase": phase_,
                         "instance_id": s["instance_id"], "option": s["option"], "layout": s["layout"], "model": s["model"],
                         "seed": s["seed"], "reason": why, "detail": str(detail)[:DETAIL_CAP], "label": label})

    def unlabelled(s: dict, key: str, ph: str, why: str, detail="", lr=None, sr=None, an=None, *, time_capped: bool = False) -> None:
        """A planned run with no usable label: a row, never an R or C input. Part 5 counts it as unknown (label "unknown"), except a run
        ended by the time cap, which has no label at all (None) and is counted apart (science, #76, 22:28Z). In the pilot it is a set N
        packet if its directory holds code (queue.assign_sets); `packet_problem` says only what is wrong with the directory."""
        run_dir = str((an or {}).get("run_dir") or "")
        rows.append({"run_key": s["run_key"], "run_dir": run_dir, "instance_id": s["instance_id"],
                     "option": s["option"], "layout": s["layout"], "model": s["model"], "seed": s["seed"], "phase": ph,
                     "label": None if time_capped else "unknown", "label_raw": None, "label_reasons": list((lr or {}).get("reasons") or []),
                     "notes": [], "decoded_not_delivered": None, "delivered_not_decoded": None, "block": s["block"], "key": key,
                     "attempt": (an or {}).get("attempt"), "out_of_cohort": bool(sr.out_of_cohort) if sr is not None else False,
                     "packet_problem": _packet_problem(run_dir) if run_dir else "no_run_dir_recorded",
                     "instrument_label": (lr or {}).get("label"), "unlabelled": True, "time_capped": time_capped,
                     "unlabelled_reason": why, "unlabelled_detail": str(detail)[:DETAIL_CAP]})

    for s in runs:
        k, block, key = s["run_key"], s["block"], _record_key(s)
        ph = BLOCK_PHASE.get(block) or phase
        if key is None:
            exclude(s, key, "bad_store_row", f"option {s['option']!r}, layout {s['layout']!r}", phase_=ph)
            continue
        if ph is None:
            exclude(s, key, "no_inspection_phase", f"block {block!r} is in none of {sorted(BLOCK_PHASE)}; pass --phase", phase_=ph)
            continue
        lr, sr, an = labels.get(k), scored.get((block, key)), analysed.get((block, key))
        lab_info = None if lr is None else lr.get("label")
        if s["exclude_from_analysis"] and ph != "calibration":
            exclude(s, key, "flagged_exclude_from_analysis", phase_=ph, label=lab_info)
            continue
        if s["status"] != "done":          # never started, still pending (a harness error is re-queued as pending), or out of retries
            if s["status"] == "infra_exhausted":
                why, detail = "infra_exhausted", "; ".join((exhausted.get(k) or {}).get("reasons") or [])
            else:
                why, detail = f"not_done:{s['status']}", ""
            unlabelled(s, key, ph, why, detail)
            continue
        miss = [n for n, v in (("run_labels", lr), ("scored_rows", sr), ("infra analysed_attempts", an)) if v is None]
        if miss:
            why = f"pipeline_failed:{failed[(block, key)]}" if (block, key) in failed else "no_pipeline_output"
            unlabelled(s, key, ph, why, f"missing from: {', '.join(miss)}", lr, sr, an)
            continue
        have = (an["attempt"], an["run_dir"])
        if store_done.get(k) != have or lr.get("attempt") != an["attempt"] or sr.attempt != an["attempt"]:
            unlabelled(s, key, ph, "pipeline_output_stale",
                       f"store done attempt {store_done.get(k, (None,))[0]}, infra {an['attempt']}, labels {lr.get('attempt')}, "
                       f"scored {sr.attempt}", lr, sr, an)
            continue
        if sr.infra_failure:
            unlabelled(s, key, ph, "infra_failure_attempt", f"attempt {sr.attempt}", lr, sr, an)
            continue
        if not sr.finished:
            # The time cap is the run's TERMINATION, never its `invalid_reason`: score_run takes that from the report or the mask first,
            # so a capped run with no report reads as a report reason.
            capped = sr.termination == Termination.TIME_CAP
            if capped:
                unlabelled(s, key, ph, "time_cap", f"ended by the time cap; the scored row's invalid_reason is {sr.invalid_reason}",
                           lr, sr, an, time_capped=True)
            else:
                unlabelled(s, key, ph, f"not_finished:{sr.invalid_reason}", "no analysis label: the run has no valid report and mask",
                           lr, sr, an)
            continue
        label = None if sr.label is None else sr.label.value
        if label is None:
            unlabelled(s, key, ph, "label_missing", "", lr, sr, an)
            continue
        if lab_info is not None and lab_info != label:
            unlabelled(s, key, ph, "label_files_disagree", f"scored_rows {label}, run_labels {lab_info}", lr, sr, an)
            continue
        flags = lr.get("flags") or {}
        dnd, ndd = _flag(flags.get("decoded_not_delivered")), _flag(flags.get("delivered_not_decoded"))
        if "invalid" in (dnd, ndd):
            exclude(s, key, "cross_check_flag_invalid", f"decoded_not_delivered {flags.get('decoded_not_delivered')!r}, "
                    f"delivered_not_decoded {flags.get('delivered_not_decoded')!r}", phase_=ph, label=label)
            continue
        run_dir = an["run_dir"]
        problem = _packet_problem(run_dir) if run_dir else "no_run_dir_recorded"    # a row all the same: queue.build refuses it into `refused`
        if problem and exclude_unbuildable:
            exclude(s, key, problem, run_dir, phase_=ph, label=label)
            continue
        raw = sr.label_raw.value if sr.label_raw is not None else flags.get("raw_label")
        rows.append({"run_key": k, "run_dir": str(run_dir or ""), "instance_id": s["instance_id"], "option": s["option"],
                     "layout": s["layout"], "model": s["model"], "seed": s["seed"], "phase": ph, "label": label,
                     "label_raw": raw if raw in LABELS else None, "label_reasons": list(lr.get("reasons") or []),
                     "notes": list(lr.get("notes") or []), "decoded_not_delivered": dnd, "delivered_not_decoded": ndd,
                     "block": block, "key": key, "attempt": an["attempt"], "out_of_cohort": bool(sr.out_of_cohort),
                     "packet_problem": problem, "instrument_label": lab_info, "unlabelled": False, "time_capped": False,
                     "unlabelled_reason": None, "unlabelled_detail": ""})
    # what the pipeline's files hold of runs the store does not: a stale or foreign output, never dropped
    known = {r["run_key"] for r in runs}
    seen = {k for k in labels} | {f"{b}__{key}" for b, key in scored} | {a["run_key"] for a in account.analysed}
    for k in sorted(seen - known):
        excluded.append({"run_key": k, "block": k.split("__", 1)[0], "key": None, "phase": None, "instance_id": None,
                         "option": None, "layout": None, "model": None, "seed": None, "reason": "not_in_campaign_store",
                         "detail": "in the pipeline output, not in state.sqlite", "label": (labels.get(k) or {}).get("label")})
    if len(rows) + len(excluded) != len(runs) + len(seen - known):
        raise PopulationError(f"accounting: {len(rows)} rows + {len(excluded)} excluded != {len(runs)} runs + {len(seen - known)} foreign")
    rows.sort(key=lambda r: r["run_key"])
    excluded.sort(key=lambda r: r["run_key"])
    try:
        assign_sets(rows, seed=0)      # the rows are what the queue takes: refuse here what it would refuse (the sets are not used)
    except ValueError as e:
        raise PopulationError(f"rows the queue refuses: {e}") from e
    return rows, excluded


def summary(rows: list[dict], excluded: list[dict]) -> dict:
    """Counts only: no run key, path or per-run label."""
    return {"rows": len(rows), "excluded": len(excluded),
            "by_label": dict(sorted(collections.Counter("time_capped" if r["time_capped"] else r["label"] for r in rows).items())),
            "by_option_layout": dict(sorted(collections.Counter(f"{r['option']}/{r['layout']}" for r in rows).items())),
            "by_phase": dict(sorted(collections.Counter(r["phase"] for r in rows).items())),
            "packet_problems": sum(1 for r in rows if r["packet_problem"]),
            "unlabelled_by_phase": dict(sorted(collections.Counter(r["phase"] for r in rows if r["unlabelled"]).items())),
            "time_capped_by_phase": dict(sorted(collections.Counter(r["phase"] for r in rows if r["time_capped"]).items())),
            "excluded_by_phase": dict(sorted(collections.Counter(str(e["phase"]) for e in excluded).items())),
            "unlabelled_instrument_decided_by_phase": dict(sorted(collections.Counter(
                r["phase"] for r in rows if r["unlabelled"] and r["instrument_label"] in ("complete", "omitting")).items())),
            "unlabelled_by_reason": dict(sorted(collections.Counter(
                r["unlabelled_reason"].split(":")[0] for r in rows if r["unlabelled"]).items())),
            "excluded_by_reason": dict(sorted(collections.Counter(e["reason"].split(":")[0] for e in excluded).items())),
            "excluded_labelled_unknown": sum(1 for e in excluded if e["label"] == "unknown")}


def _atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write(rows: list[dict], excluded: list[dict], out) -> tuple[Path, Path]:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    side = out.with_name(out.stem + ".excluded.jsonl")
    _atomic(out, "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    _atomic(side, "".join(json.dumps(e, sort_keys=True) + "\n" for e in excluded))
    return out, side


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.inspection.population", description=__doc__.split("\n\n")[0])
    ap.add_argument("--campaign-root", required=True, help="holds state.sqlite (read-only here)")
    ap.add_argument("--pipeline-out", help="the pipeline's output directory (default: CAMPAIGN_ROOT/pipeline)")
    ap.add_argument("--infra", help="the infra export (default: PIPELINE_OUT/infra.json)")
    ap.add_argument("--phase", choices=PHASES, help="the phase of a run whose block has none of its own (the block decides otherwise)")
    ap.add_argument("--exclude-unbuildable", action="store_true",
                    help="exclude (instead of marking) a run whose directory lacks its transcript or code cells")
    ap.add_argument("--out", required=True, help="population.jsonl; the excluded runs go to population.excluded.jsonl beside it")
    a = ap.parse_args(argv)
    root = Path(a.campaign_root)
    try:
        rows, excluded = rows_from_pipeline(Path(a.pipeline_out) if a.pipeline_out else root / "pipeline", campaign_root=root,
                                            phase=a.phase, infra=a.infra, exclude_unbuildable=a.exclude_unbuildable)
    except PopulationError as e:
        print(f"icsa.inspection.population: {e}", file=sys.stderr)
        return 2
    write(rows, excluded, a.out)
    print(json.dumps(summary(rows, excluded), sort_keys=True))
    if not any(not r["unlabelled"] for r in rows):
        print("icsa.inspection.population: no result run to inspect", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
