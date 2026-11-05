"""What the other lanes read from #12's runs: the dossier's `scripted_pipeline` and `scripted_timing`.

Formats and rules are the dossier's (`icsa/dossier/README.md`, `criteria.py`); a test runs these files through its own checks.

The cap is per block, from that block's cells, run as that block's mix (science's amendment on #12, 1 Nov 17:30Z). `blocks` has
each block's `cap`: each run against the median single run of its own instance, which a slow instance cannot loosen
(Codex, 1 Nov). `cap_dossier_rule` beside it is the dossier's rule on that block's cells (worst single run as the baseline);
`cap_rules_agree` says whether they match; a disagreement is reported, not resolved here. `concurrency_cap` is set only when the blocks' caps agree: the dossier's c6 reads
one cap over six cells, so until it reads `blocks` a split cap leaves it MISSING rather than recomputing a wrong one over the
levels the blocks share. Block 2's cap is not applied here: the science agent decides it, with the numbers.

  `wall_s` at a level is the WORST clean run of the cell at that level, because the time-cap rule (b) takes the full-data run
  time at the cap from it, and "keeps" must not be averaged away. `single_run_wall_s` is the worst clean single run, so the
  ratio compares like with like: a median would fail level 1 whenever instances differ by more than a quarter, with no
  concurrency at all. The curve has a level-1 point from those same runs: without it, a host where only level 1 passes
  would read as "no cap". `errors` counts the runs that were not clean (an OOM kill is one, science, #9).

Beside each point: network time and CPU seconds of the read and the compute, and CPU seconds and peak memory per container, so
the curve shows which limit it hit. Retried reads and timeouts are counted per level and apart from `errors` (the lead's input
from #3): whether a retried timeout counts as an error is the science agent's call. The audit-log state comes from the batches'
manifests.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from . import curve as Cv
from .metrics import RETRY_BEHAVIOUR

DISK_ERRORS = ("No space left on device", "ENOSPC", "Disk quota exceeded")


def _within_disk(rs: list[dict]) -> bool:
    return not any(any(m in str(e) for m in DISK_ERRORS) for r in rs for e in (r.get("errors") or []))


def _gate(r: dict) -> dict | None:
    """The run's gate error counts; None when they are not known, which is not zero: a record that was lost, a run with no sandbox record at all, and every run of M, which has no REST
    data path."""
    return ((r.get("sandbox") or {}).get("gate_transfers") or {}).get("errors")


def _gate_sum(gate: list[dict | None], *keys: str) -> int | None:
    """Over a point's runs; None when any run's counts are not known, never that run counted as zero."""
    return None if any(g is None for g in gate) else sum(g.get(k, 0) for g in gate for k in keys)


def scripted_pipeline(runs: list[dict]) -> dict:
    """{"cells": [{option, layout, completed, correct}]}: criterion 5. A cell with no run is absent, which reads as MISSING.

    `completed`: every run of the cell finished clean, with the script's result (an OOM kill or a gate error is not clean,
    whatever the output). `correct`: every run equals the frozen truth. Any failed run makes the cell false: the runs of a
    cell are not a best-of."""
    cells: dict[tuple[str, str], list[dict]] = {}
    for r in runs:
        cells.setdefault((r["option"], r["layout"]), []).append(r)
    out = []
    for (o, la), rs in sorted(cells.items()):
        out.append({"option": o, "layout": la, "completed": all(r.get("script") is not None and Cv.clean(r) for r in rs),
                    "correct": all((r.get("compare") or {}).get("equal") is True for r in rs),
                    "runs": len(rs), "instances": sorted({r["instance_id"] for r in rs})})
    return {"format": "icsa-scripted-pipeline-v1", "cells": out}


def _median(xs) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 3) if xs else None


def _level_one_verdicts(rs: list[dict], single_read: dict) -> tuple[bool, bool]:
    """(wall, read) verdicts of the single runs as the level-1 point: clean runs exist, and every one has a measured read phase
    and a positive read-phase baseline. A missing stamp is no pass."""
    clean = [r for r in rs if Cv.clean(r)]
    read = bool(clean) and all(Cv.read_phase_s(r) is not None and (single_read.get((r["option"], r["layout"], r["instance_id"])) or 0) > 0
                               for r in clean)
    return bool(clean), read


def _point(level: int, rs: list[dict], single: dict, row: dict | None = None, single_read: dict | None = None, host_ratios: dict | None = None) -> dict:
    """`row` is the level's `curve.level_table` row (level >= 2): its two ratio verdicts are exported beside the numbers, so the
    dossier applies the same rule and not its own. Without one (level 1, or a level with no counted run) they follow
    `_level_one_verdicts` or are False. `host_ratios` (level >= 2 only; level 1 is the baselines themselves): each run's ratio is to its own host's
    reference (`curve.run_reference`), as the row's verdicts are. A row with a `rule` (the duty-cycle curve's median rule) has it copied to the point, so
    the dossier's own cap rule does not judge that point's worst wall against the single run again (`criteria.concurrency_cap`)."""
    clean = [r for r in rs if Cv.clean(r)]
    wall_ok, read_ok = (row["passes_wall"], row["passes_read"]) if row else (_level_one_verdicts(rs, single_read or {}) if level == 1 else (False, False))
    ratios = [r["wall_s"] / (single[(r["option"], r["layout"], r["instance_id"])] if host_ratios is None else Cv.run_reference(single, None, r, host_ratios)[0])
              for r in clean if (r["option"], r["layout"], r["instance_id"]) in single]
    gate = [_gate(r) for r in rs]
    stamps = [(r.get("script") or {}).get("stamps_s") or {} for r in clean]
    roles = sorted({role for r in rs for role in (r.get("containers") or {})})
    return {"concurrency": level, "wall_s": max(r["wall_s"] for r in clean) if clean else None,
            "errors": len(rs) - len(clean), "within_disk": _within_disk(rs), "runs": len(rs),
            "wall_ratio_ok": wall_ok, "read_ratio_ok": read_ok,
            "median_wall_s": round(statistics.median(r["wall_s"] for r in clean), 3) if clean else None,
            "max_ratio_own_instance": round(max(ratios), 3) if ratios else None,
            "oom_kills": sum(v or 0 for r in rs for v in (r.get("oom_kills") or {}).values()),
            "median_read_s": _median(st["read_done"] - st["listing_done"] for st in stamps if "read_done" in st and "listing_done" in st),
            "median_compute_s": _median(st["compute_done"] - st["read_done"] for st in stamps if "compute_done" in st and "read_done" in st),
            "median_cpu_read_s": _median(((r.get("script") or {}).get("cpu_s") or {}).get("read") for r in clean),
            "median_cpu_compute_s": _median(((r.get("script") or {}).get("cpu_s") or {}).get("compute") for r in clean),
            "containers": {role: {"median_cpu_s": _median(((r.get("containers") or {}).get(role) or {}).get("cpu_s") for r in clean),
                                  "max_peak_bytes": max((((r.get("containers") or {}).get(role) or {}).get("peak_bytes") or 0 for r in rs), default=0)}
                           for role in roles},
            "upstream_retries": _gate_sum(gate, "upstream_retries"),
            "upstream_stale": _gate_sum(gate, "upstream_stale"),
            "gate_errors": _gate_sum(gate, "gate_5xx", "gate_resets"),
            "upstream_errors": _gate_sum(gate, "upstream_5xx", "upstream_resets"),
            "timeouts_by_tag": _timeouts(rs),
            **({"rule": row["rule"]} if row and "rule" in row else {})}


def _timeouts(rs: list[dict]) -> dict:
    """Upstream timeouts per request type (attributes and content may behave differently under load, #3)."""
    out: dict[str, int] = {}
    for r in rs:
        for tag, t in ((r.get("gate_requests") or {}).get("by_tag") or {}).items():
            n = int(t.get("upstream_timeouts") or 0)
            if n:
                out[tag] = out.get(tag, 0) + n
    return out


def scripted_timing(single_runs: list[dict], curve_runs: list[dict], *, audit_log: str | None = None,
                    level_vetoes: dict[int, set[int]] | None = None,
                    duty_decisions: dict[tuple[int, int, int], str | None] | None = None, host_ratios: dict | None = None,
                    duty_ladders: dict[int, dict] | None = None) -> dict:
    """{"cells": {"T__S1": {single_run_wall_s, provider_io_bytes, curve: [...]}}, "blocks": {...}, "concurrency_cap": n}.

    `level_vetoes`: block -> the levels earlyoom failed (`curve.earlyoom_vetoes`). The duty-cycle curve's own failures (`duty.report_vetoes`; review
    S1, findings 4 and 5) are taken from the counted records that carry a duty profile, and from `duty_decisions` (`curve.duty_decisions`) when given: a
    level that waited for the pacer, lacks part of its plan, has no decision line or a failed one is failed here as `cmd_curve` failed it, in the
    exported points and the cap alike, and listed beside the block's `earlyoom_failed_levels` as `duty_failed_levels` (level -> why; present only when
    there is one). The registered mix carries no duty profile and is judged as before.

    `duty_ladders` (`curve.duty_ladders`; amendment 34(a)): block -> the ladder its duty-cycle curve ran. A block with one gets `not_run_levels`: the ladder's levels (frozen
    and floor) that have no decision line and no counted record, sorted: the curve's table has those rows marked not run. They are NOT added to the cells' curves (the
    dossier's rule takes only measured levels). A block with no ladder gets no new key.

    `host_ratios` (`curve.load_host_ratios`, as the curve was run with: the report finds the curve's copy, `curve.find_host_ratios`): every counted run is
    judged against its own host's reference, in the table, the points and the cap, as the curve decided; the result then has `host_reference`
    (`curve.host_reference_record`). Without it the result is as it always was, with no new key."""
    from ..dossier.criteria import concurrency_cap as dossier_cap
    from . import duty as DC
    from .plans import BLOCK_CELLS
    not_single = sorted(r.get("run_key", "?") for r in single_runs
                        if (r["extra"].get("pool_workers") or 1) > 1 or "level" in r["extra"])
    if not_single:
        raise ValueError(f"not single runs (a pool or a curve level): {not_single[:5]}: they would inflate the baseline "
                         "and loosen the cap")
    single_all: dict[tuple[str, str], list[dict]] = {}
    for r in single_runs:
        single_all.setdefault((r["option"], r["layout"]), []).append(r)
    counted = Cv.counted(curve_runs)
    duty_failed = DC.report_vetoes(counted, duty_decisions)
    levels: dict[tuple[str, str, int], list[dict]] = {}
    for r in counted:
        levels.setdefault((r["option"], r["layout"], int(r["extra"]["level"])), []).append(r)
    own = Cv.single_run_walls(single_runs)
    own_read = Cv.single_read_phases(single_runs)
    table = Cv.level_table(own, counted, single_read=own_read, host_ratios=host_ratios)
    rows = {(t["option"], t["layout"], t["level"]): t for t in table}
    cells = {}
    for (o, la) in sorted({k[:2] for k in levels} | set(single_all)):
        rs = single_all.get((o, la), [])
        clean = [r for r in rs if Cv.clean(r)]
        io = [(r.get("bytes") or {}).get("between_sites_rx") for r in clean]
        io = [x for x in io if x is not None]
        pts = [_point(1, rs, own, single_read=own_read)] if rs else []
        pts += [_point(lv, levels[(o, la, lv)], own, rows.get((o, la, lv)), host_ratios=host_ratios) for lv in sorted(k[2] for k in levels if k[:2] == (o, la))]
        cells[f"{o}__{la}"] = {"single_run_wall_s": max(r["wall_s"] for r in clean) if clean else None,
                               "single_run_median_s": round(statistics.median(r["wall_s"] for r in clean), 3) if clean else None,
                               "provider_io_bytes": int(statistics.median(io)) if io else None,
                               "single_runs": len(rs), "curve": pts}
    blocks = {}
    for b, block_cells in BLOCK_CELLS.items():
        names = [(o.value, la.value) for o, la in block_cells]
        keys = [f"{o}__{la}" for o, la in names]
        entry: dict = {"cells": keys, "cap": None, "cap_dossier_rule": None, "cap_rules_agree": None, "wall_at_cap_s": None,
                       "levels": sorted({int(r["extra"]["level"]) for r in counted if (r["option"], r["layout"]) in names})}
        if all(k in cells and cells[k]["curve"] for k in keys):
            vetoed = (level_vetoes or {}).get(b, set())       # an earlyoom kill in the level's window fails it, whatever its counted runs did (curve.level_passes)
            duty = duty_failed.get(b, {})                     # so does what the duty-cycle curve fails a level for beyond its timing table
            failed = vetoed | set(duty)
            entry["earlyoom_failed_levels"] = sorted(vetoed)
            if duty:
                entry["duty_failed_levels"] = {str(lv): why for lv, why in sorted(duty.items())}
            entry["levels"] = sorted({*entry["levels"], *failed})   # a level whose every run infrastructure ended has no record left here, and it still failed
            for k in keys:                                    # in the exported points too, or the dossier's own rule finds the level passing
                have = {p["concurrency"] for p in cells[k]["curve"]}
                cells[k]["curve"] += [_point(lv, [], own) for lv in sorted(failed - have)]
                cells[k]["curve"].sort(key=lambda p: p["concurrency"])
                for p in cells[k]["curve"]:
                    if p["concurrency"] in failed:
                        if p["concurrency"] in vetoed:
                            p["earlyoom_failed"] = True
                        if p["concurrency"] in duty:
                            p["duty_failed"] = True
                        p["errors"] = max(p["errors"], 1)
                        p["wall_ratio_ok"] = p["read_ratio_ok"] = False
            dossier, _ = dossier_cap({k: cells[k] for k in keys})
            judged = [dict(t, passes=False) if t["level"] in failed else t for t in table]
            cap = Cv.cap(judged, names, entry["levels"], own, own_read)["contiguous_cap"]   # the last pass before the first fail (science, #2); each run against its own instance's single run
            entry.update(cap=cap, cap_dossier_rule=dossier, cap_rules_agree=cap == dossier)
            if cap is not None:
                walls = [p["wall_s"] for k in keys for p in cells[k]["curve"] if p["concurrency"] == cap]
                entry["wall_at_cap_s"] = max(w for w in walls if w is not None) if any(w is not None for w in walls) else None
        if duty_ladders and b in duty_ladders:
            ladder = duty_ladders[b]
            every = {int(x) for x in ladder["frozen"]} | ({int(ladder["floor"])} if ladder.get("floor") is not None else set())
            entry["not_run_levels"] = sorted(every - {lv for (bb, lv, _rep) in (duty_decisions or {}) if bb == b} - set(entry["levels"]))
        blocks[str(b)] = entry
    caps = {e["cap"] for e in blocks.values()}
    return {"format": "icsa-scripted-timing-v2", "cells": cells, "blocks": blocks, "audit_log": audit_log,
            "retry_behaviour": RETRY_BEHAVIOUR, "concurrency_cap": caps.pop() if len(caps) == 1 else None,
            "block_2_decided_by": "the science agent, with these numbers (amendment on #12, 1 Nov 17:30Z)",
            **({"host_reference": Cv.host_reference_record(host_ratios)} if host_ratios is not None else {})}


def audit_state(*dirs: Path | str) -> str | None:
    """The audit-log state the batches declared in their manifests: one value, or `mixed`, or None if none declared it."""
    states = set()
    for d in dirs:
        for m in Path(d).glob("MANIFEST_*.json"):
            s = json.loads(m.read_text()).get("audit_log")
            if s:
                states.add(s)
    return states.pop() if len(states) == 1 else ("mixed" if states else None)
