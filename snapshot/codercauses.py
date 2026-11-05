"""Rule-based causes for the runs the coders resolved to omitting (#34, science 5 Nov 12:19Z, item 1), from the coders' exact missing extents.

    python -m snapshot.codercauses <seal> --answers-root DIR [--t T]        # writes <seal>/coder_replay/coder_causes.csv and coder_causes.meta.json (mode 600/700, sealed)

`causes.csv` (the pipeline's) covers the runs the INSTRUMENT labelled omitting and the unfinished ones. A run the instrument left `unknown` and both coders resolved to `omitting` (decision route
`inspection`) has none. Here every such run gets a row: coded, or with the reason it could not be.

Coded by the frozen rule coder, `icsa.causes.rules.code_run`, on a `RunEvidence` built from the pipeline's scored row and run record, label `omitting`, and as `analysed` the extent the coders
extracted (the required units minus the exact (day, sea cell) pairs their extraction leaves out; the dates they extracted outside the required set are kept as other days, which is what a
substitution is). The read extent, the listing and the downloads are NOT observed for these runs (the instrument lost track of them, and the pipeline keeps no extents), so:

- CAN be coded: infra_failure and the termination causes (from the record), wrong_subset_period and wrong_subset_baseline (whole days missing, intact other part, other days extracted at least as many),
  early_stop, analysis_error_on_covered_data, unknown.
- CANNOT be coded: truncated_listing, skipped_or_partial_read, read_not_used and wrong_subset_region. They need the read extent or the listing. The row's `trail` says `read=not_observed`.
- A run whose two extractions differ, or leave a part CANNOT TELL, has no exact extent: a row with `why_not_coded`.

`cause` is the codebook's, strictly. `cause_window_rule` is the same unless the missing set is a WHOLE-DAY shortfall of exactly one part with nothing else missing (a window short by rule, e.g. one edge day
per baseline year, whole years, a target window short at an edge), in which case it is wrong_subset_baseline or wrong_subset_period even without substituted days (science's reading, 12:19Z); a
cap, an infra failure or a cause the rule coder found other than early_stop/unknown is never overridden. `cause_detail` says the shape: baseline=<intact | whole_years:.. | all_years |
one_edge_day_per_year:lead|trail | edge_days_per_year:lead<a>+trail<b> | mixed:<n>_years>, target=<intact | all_days | edge_days:lead<a>+trail<b> | interior:<n>..>, cells=<..>.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse    # noqa: E402
import csv         # noqa: E402
import json        # noqa: E402
import os          # noqa: E402
import tempfile    # noqa: E402
import time        # noqa: E402
from pathlib import Path    # noqa: E402

import numpy as np    # noqa: E402

from icsa import grid    # noqa: E402
from icsa.causes import codebook as CB    # noqa: E402
from icsa.causes.evidence import RunEvidence    # noqa: E402
from icsa.causes.rules import Coding, code_run    # noqa: E402
from icsa.extent import Extent, PartedExtent    # noqa: E402
from icsa.inspection import compare as CMP    # noqa: E402
from icsa.records import OmissionLabel    # noqa: E402

from . import coderreplay as CR    # noqa: E402

COLUMNS = ["run_key", "block", "key", "instance_id", "option", "layout", "model", "coded", "cause", "secondary", "cause_window_rule", "cause_detail", "window_baseline", "window_target",
           "window_cells", "other_days_extracted", "why_not_coded", "trail"]


# ---------------------------------------------------------------------------------------------------------------------------------- the shape of what is missing
def _edges(days: list, missing: set) -> tuple[int, int, int]:
    """(leading, trailing, interior) missing days of a window (a sorted list of dates), `missing` a subset of it."""
    lead = 0
    while lead < len(days) and days[lead] in missing:
        lead += 1
    trail = 0
    while trail < len(days) - lead and days[len(days) - 1 - trail] in missing:
        trail += 1
    return lead, trail, len(missing) - lead - trail


def window_shape(g: np.ndarray, day_list: list, req: CMP.Required) -> dict:
    """What the missing grid looks like: per part and for the cells. 'whole' days are days lacking every sea cell that is not missing on every day (those cells are the `cells` shape)."""
    every = g.all(axis=0) if g.shape[0] else np.zeros(g.shape[1], bool)
    n_sea = g.shape[1]
    cells = "intact" if not every.any() else "everything_missing" if every.all() else f"cells_missing_every_day:{int(every.sum())}"
    rest = g[:, ~every]
    whole = rest.all(axis=1) if rest.shape[1] else np.zeros(g.shape[0], bool)
    partial = bool((rest.any(axis=1) & ~whole).any()) if rest.shape[1] else False
    if partial:
        cells += "+partial_cell_days" if cells != "intact" else "partial_cell_days"
    dpos = {d: k for k, d in enumerate(day_list)}
    miss = {d for d in day_list if whole[dpos[d]]}
    years = sorted(req.baseline_days)
    per_year = {}
    for y in years:
        ds = sorted(req.baseline_days[y])
        m = {d for d in ds if d in miss}
        per_year[y] = "whole" if m and len(m) == len(ds) else "none" if not m else _edges(ds, m)
    hit = {y: v for y, v in per_year.items() if v != "none"}
    if not hit:
        base = "intact"
    elif len(hit) == len(years) and all(v == "whole" for v in hit.values()):
        base = "all_years"
    elif all(v == "whole" for v in hit.values()):
        base = "whole_years:" + ",".join(str(y) for y in sorted(hit))
    elif len(hit) == len(years) and len(set(hit.values())) == 1 and hit[years[0]] != "whole" and hit[years[0]][2] == 0:
        lead, trail, _ = hit[years[0]]
        base = f"one_edge_day_per_year:{'lead' if lead else 'trail'}" if lead + trail == 1 else f"edge_days_per_year:lead{lead}+trail{trail}"
    else:
        base = f"mixed:{len(hit)}_years"
    td = sorted(req.target_days)
    mt = {d for d in td if d in miss}
    if not mt:
        tgt = "intact"
    elif len(mt) == len(td):
        tgt = "all_days"
    else:
        lead, trail, inner = _edges(td, mt)
        tgt = f"edge_days:lead{lead}+trail{trail}" + (f"+interior:{inner}" if inner else "")
    return {"baseline": base, "target": tgt, "cells": cells, "partial": partial, "every_cells": int(every.sum()), "n_sea": n_sea,
            "whole_day_shortfall_baseline_only": base != "intact" and tgt == "intact" and not every.any() and not partial,
            "whole_day_shortfall_target_only": tgt != "intact" and base == "intact" and not every.any() and not partial}


def other_days(ans: dict, req: CMP.Required) -> set:
    """The dates the extraction covers outside the required set (the substitution, if any). Cells and exceptions are not applied: a date is 'extracted' if some range of the answer has it."""
    covered = set()
    for e in ans["baseline"]:
        if e["status"] == "RANGES":
            covered |= CMP._days(e["ranges"])
    if ans["target"]["status"] == "RANGES":
        covered |= CMP._days(ans["target"]["ranges"])
    return covered - req.all_days()


def analysed_with_other_days(analysed: PartedExtent, extra: set) -> PartedExtent:
    """`analysed` plus the extracted days outside the required set (all sea cells), in the baseline part: the rule coder counts a day outside the required set as 'other' wherever it stands."""
    if not extra:
        return analysed
    b = analysed.baseline
    idx = np.array(sorted(grid.day_index(d) for d in extra), np.int64)
    days = np.union1d(b.days, idx)
    mask = np.zeros((days.size, *b.box.shape), bool)
    mask[np.searchsorted(days, b.days)] = b.mask
    sea = analysed.target.mask.any(axis=0) if analysed.target.days.size else b.mask.any(axis=0)
    mask[np.searchsorted(days, idx)] = sea
    return PartedExtent(Extent(b.box, days, mask), analysed.target)


# ---------------------------------------------------------------------------------------------------------------------------------- the rows
def _record_facts(run_dir: str) -> dict | None:
    rd = Path(run_dir)
    for n in ("run_record.json", "run.json"):
        try:
            d = json.loads((rd / n).read_text())
            return {"invalid_tool_args_rounds": int(d.get("invalid_tool_args_rounds") or 0), "error_type": d.get("error_type"), "infra_reason": d.get("infra_reason"),
                    "transcript_path": d.get("transcript_path") or "", "code_cells_path": d.get("code_cells_path") or "", "output_dir": d.get("output_dir") or "output"}
        except (OSError, ValueError):
            continue
    return None


def _caveats(run_dir: str, facts: dict) -> str | None:
    try:
        c = json.loads((Path(run_dir) / facts["output_dir"] / "report.json").read_text()).get("caveats")
    except (OSError, ValueError, AttributeError):
        return None
    return c if isinstance(c, str) else None


def _cells_path(run_dir: str, facts: dict) -> str:
    """The code the labeller scanned (the sandbox's cell log) if there is one, else the harness's copy: relative to the run directory."""
    rd = Path(run_dir)
    for c in (rd / "cells" / "cells.jsonl", rd / facts["code_cells_path"] if facts["code_cells_path"] else None):
        if c is not None and c.is_file():
            return c.relative_to(rd).as_posix()
    return facts["code_cells_path"]


def evidence(item: dict, scored, facts: dict, required: PartedExtent, analysed: PartedExtent) -> RunEvidence:
    return RunEvidence(block=item["block"], run_key=item["key"], option=scored.run.option, layout=scored.run.layout, termination=scored.termination, finished=scored.finished,
                       label=OmissionLabel.OMITTING, required=required, analysed=analysed, read=None, listing=None, listing_disagrees=None,
                       infra_failure=scored.infra_failure, infra_reason=facts["infra_reason"], attempt=scored.attempt, invalid_tool_args_rounds=facts["invalid_tool_args_rounds"],
                       correct=scored.correct, complete_extent=False, cf_computation_f1=scored.cf_computation_f1, self_report_complete=scored.self_report_complete,
                       error_type=facts["error_type"], caveats=_caveats(item["run_dir"], facts),
                       trace_paths={"transcript": facts["transcript_path"], "code_cells": _cells_path(item["run_dir"], facts)})


def causes_rows(seal: Path, answers_root: Path, ext: CR.Extents | None = None) -> list[dict]:
    return [c["row"] for c in coded_runs(seal, answers_root, ext)]


def coded_runs(seal: Path, answers_root: Path, ext: CR.Extents | None = None) -> list[dict]:
    """One dict per resolved-omitting run: {"row": the table row, "ev": its RunEvidence or None, "coding": the rule coder's Coding or None, "run_dir": ...}."""
    seal = Path(seal)
    m, recs, masks = CR._manifest()
    ext = ext or CR.Extents(recs, masks)
    decisions = json.loads((seal / "inspection" / "decisions.json").read_text())
    pop = CR._population(seal)
    from icsa.analysis.adapter import load_jsonl
    sp = seal / "out" / "pipeline" / "scored_rows.jsonl"
    scored = {(r.block, r.run.key()): r for r in load_jsonl(sp)} if sp.is_file() else {}
    rows, results = [], []
    for pid in sorted(decisions["packets"]):
        p = decisions["packets"][pid]
        dec = p.get("decision") or {}
        if p.get("set") not in ("R", "C") or dec.get("label") != "omitting" or dec.get("route") != "inspection":
            continue
        row_pop = pop.get(p["run_key"]) or {}
        it = {"run_key": p["run_key"], "block": row_pop.get("block"), "key": row_pop.get("key"), "instance_id": p.get("instance_id"), "option": p.get("option"), "layout": p.get("layout"),
              "model": p.get("model")}
        out = {c: it.get(c, "") for c in COLUMNS}
        out.update(coded="false", cause="", secondary="", cause_window_rule="", cause_detail="", why_not_coded="")
        rows.append(out)
        res = {"row": out, "ev": None, "coding": None, "run_dir": row_pop.get("run_dir") or "", "days": None}
        results.append(res)
        try:
            d1, d2 = (p["coders"][c]["detail"] for c in p["pair"])
            dm = CR.decide.decomposition(d1, d2)
            if not dm["computable"]:
                raise CR.ReplayError(CR.WHY.get(dm["why"], "extraction_not_exact"))
            if not row_pop or not row_pop.get("run_dir"):
                raise CR.ReplayError("no_run_dir" if row_pop else "not_in_population")
            sc = scored.get((row_pop.get("block"), row_pop.get("key")))
            if sc is None:
                raise CR.ReplayError("no_scored_row")
            facts = _record_facts(row_pop["run_dir"])
            if facts is None:
                raise CR.ReplayError("no_run_record")
            fin = CR.read_final(answers_root, pid, p["pair"][0])
            if fin is None:
                raise CR.ReplayError("answer_unreadable")
            req = ext.required(it["instance_id"])
            v = CMP.compare(fin["answer"], req)
            if v.extraction_sha256 != d1["extraction_sha256"] or v.missing_extent_sha256 != d1["missing_extent_sha256"]:
                raise CR.ReplayError("answer_changed_since_decision")
            g, day_list, sea_flat = CR.missing_grid(fin["answer"], req)
            if CR.grid_digest(g) != v.missing_extent_sha256:
                raise CR.ReplayError("extent_rebuild_mismatch")
            required = ext.extent(it["instance_id"])
            extra = other_days(fin["answer"], req)
            analysed = analysed_with_other_days(CR.analysed_extent(required, g, day_list, sea_flat), extra)
            ev = evidence(row_pop, sc, facts, required, analysed)
            coding = code_run(ev)
            if not isinstance(coding, Coding):
                raise CR.ReplayError("not_coded_by_the_rules")
            res["ev"], res["coding"] = ev, coding
            res["days"] = {**CR.missing_summary(g, day_list, req), "other_days": len(extra)}        # what a reader needs to judge a shortfall: which days, and how many other days stand in
            shape = window_shape(g, day_list, req)
            strict = coding.primary
            wr = strict
            if strict in ("early_stop", "unknown"):
                if shape["whole_day_shortfall_baseline_only"]:
                    wr = "wrong_subset_baseline"
                elif shape["whole_day_shortfall_target_only"]:
                    wr = "wrong_subset_period"
            out.update(coded="true", cause=strict, secondary=";".join(coding.secondary), cause_window_rule=wr,
                       cause_detail=f"baseline={shape['baseline']};target={shape['target']};cells={shape['cells']}",
                       window_baseline=shape["baseline"], window_target=shape["target"], window_cells=shape["cells"], other_days_extracted=len(extra), trail=" | ".join(coding.trail))
        except CR.ReplayError as e:
            out["why_not_coded"] = e.reason
        except (KeyError, TypeError, ValueError) as e:
            out["why_not_coded"] = f"answer_unreadable:{type(e).__name__}"
    return results


def write_rows(path: Path, rows: list[dict], header: str) -> None:
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(fd, "w", newline="") as fh:
        fh.write(header + "\n")
        w = csv.DictWriter(fh, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def run(seal: Path, answers_root: Path, t: str) -> dict:
    t0 = time.time()
    rows = causes_rows(seal, answers_root)
    out = Path(seal) / "coder_replay"
    write_rows(out / "coder_causes.csv", rows, f"# snapshot final={CR.snapshot_final(seal)} t={t}")
    why: dict[str, int] = {}
    for r in rows:
        if r["why_not_coded"]:
            k = r["why_not_coded"].split(":")[0]
            why[k] = why.get(k, 0) + 1
    meta = {"rows": len(rows), "coded": sum(r["coded"] == "true" for r in rows), "not_coded": sum(r["coded"] != "true" for r in rows), "not_coded_by_reason": dict(sorted(why.items())),
            "t": t, "seconds": round(time.time() - t0, 1), "codebook": [c.name for c in CB.CODES]}
    (out / "coder_causes.meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
    os.chmod(out / "coder_causes.meta.json", 0o600)
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m snapshot.codercauses", description=__doc__.split("\n\n")[0])
    ap.add_argument("seal")
    ap.add_argument("--answers-root", required=True)
    ap.add_argument("--t", default="unknown")
    a = ap.parse_args(argv)
    os.umask(0o077)
    try:
        meta = run(Path(a.seal), Path(a.answers_root), a.t)
    except (OSError, ValueError, KeyError, CR.ReplayError) as e:
        print(f"codercauses refused: {type(e).__name__}: {getattr(e, 'reason', '') or str(e)[:120]}", file=sys.stderr)
        return 2
    print(json.dumps({"written": True, "seconds": meta["seconds"]}, sort_keys=True))        # no count: the number of resolved-omitting runs is label-derived; meta.json (sealed) has them
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
