"""Rubric §7 and §8: the decisions stage, the K-test gate, the report and the dossier artifact.

Stages (each a plain function of files already on disk):

    decisions(key, work, required_for)   per packet: both coders' verdicts, the §5 decision
    report(decisions, key, ...)          every number of §7 (the gate) and §8 (the reporting)
    gate_artifact(report)                the compact `icsa-inspection-gate-v1` record for the dossier
    project(report, packets)             linear cost and wall-time projection from the measured packets

A set N packet (a pilot run with no label: `queue.py`) is answered and counted but NEVER scored: no part, share, kappa, rate or
coverage record reads it, and a pending one makes no part incomplete (it has its own section). "K" in a name or a line of this
report is the known-answer set; the runs ended by the time cap, which report-spec also calls K, are `time_capped` here.

Nothing is rounded into a bare rate: every figure carries its numerator and denominator. A
packet any coder has not answered (or whose answer file is stale or unreadable) is PENDING: it is
never a verdict, never an agreement, and it makes every part it touches "incomplete" unless that
part has already failed for sure. MALFORMED is no verdict: it never agrees with anything; for
kappa it is counted as CANNOT_TELL (stated in the output).

The main block's coding plan (amendment 26, `plan.py`, `--pair-plan`). A packet of the plan is scored by ITS OWN pair, from its pair record
(`answers/<packet>/pair.json`): Sol + Opus, or Opus + Sonnet. Every main-block table (kappa, set C rates, share resolved, tokens, cost) has a
row per pair and no pooled rate; one sensitivity row counts the Sol-coded runs only. A Sonnet subject run the plan left uncoded is `not_coded`:
no decision, so its `unknown` stands, listed by count and reason. The K and pilot parts (and every packet outside the plan) stay as they are,
scored by `--pair`.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import answer as answer_mod
from . import compare, decide
from . import plan as PL
from .queue import MAIN_PHASES

FORMAT_DECISIONS = "icsa-inspection-decisions-v1"
FORMAT_ANSWER = "icsa-inspection-answer-v1"
FORMAT_GATE = "icsa-inspection-gate-v1"
FORMAT_REPORT = "icsa-inspection-report-v1"
CODERS = ("codex", "claude")          # the pair this report scores: --pair (amendment 26: Opus + Sol, and the fallback Opus + Sonnet)
KNOWN_CODERS = ("codex", "claude", "sonnet")
KAPPA_CATS = ("COMPLETE", "OMITTING", "CANNOT_TELL")
PENDING = "PENDING"
OUTPUTS = ("decisions.json", "report.json", "report.md", "inspection_gate.json")
Z95 = 1.959964


# ----------------------------------------------------------------------------- decisions stage

def _read_final(work, pid, coder):
    """(final dict | None, problem str | None). A missing file is pending, not a problem."""
    p = Path(work) / "answers" / pid / coder / "final.json"
    if not p.is_file():
        return None, None
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError) as e:
        return None, f"{coder} final.json unreadable: {type(e).__name__}"
    if not isinstance(d, dict):
        return None, f"{coder} final.json is not an object"
    return d, None


def _read_lines(packets_dir, pid):
    """cell number -> code line count, from the packet's lines.json; (None, problem) when unreadable."""
    p = Path(packets_dir) / f"{pid}.lines.json"
    try:
        return {int(k): v for k, v in json.loads(p.read_text()).items()}, None
    except (OSError, ValueError, AttributeError) as e:
        return None, f"{p.name} unreadable: {type(e).__name__}"


def _coder_entry(key, pid, pk, coder, work, required_for, req_cache, problems, lines):
    final, problem = _read_final(work, pid, coder)
    if problem:
        problems.append({"pid": pid, "problem": problem})
        return {"verdict": PENDING, "detail": None, "meta": None, "note": problem}
    if final is None:
        return {"verdict": PENDING, "detail": None, "meta": None}
    if final.get("format", FORMAT_ANSWER) != FORMAT_ANSWER:
        note = f"{coder} final.json has format {final.get('format')!r}"
        problems.append({"pid": pid, "problem": note})
        return {"verdict": PENDING, "detail": None, "meta": None, "note": note}
    for field, want in (("prompt_sha256", key.get("prompt_sha256")), ("packet_sha256", pk.get("packet_sha256"))):
        if field in final and want and final[field] != want:
            note = f"{coder} final.json {field} does not match the key (stale answer)"
            problems.append({"pid": pid, "problem": note})
            return {"verdict": PENDING, "detail": None, "meta": None, "note": note}
    meta = {"usage": final.get("usage") or {}, "wall_s": final.get("wall_s"), "cost_usd": final.get("cost_usd"),
            "attempts": final.get("attempts"), "contaminated_attempts": final.get("contaminated_attempts"),
            "subagent_attempts": final.get("subagent_attempts")}
    # Registered rule 21(a) (#2, 14:28Z), and science, #76, 2 Nov 12:43Z: a coder with no valid answer within its attempts
    # (malformed, contaminated, refused, or failed by infrastructure every time) is CANNOT TELL, so the run stays unknown.
    if final.get("status") in ("malformed", "contaminated", "refused", "error"):
        why = {"contaminated": "contaminated in every attempt"}.get(final["status"], f"no valid answer within the attempt limit ({final['status']})")
        return {"verdict": "CANNOT_TELL", "detail": None, "meta": meta, "note": why, "no_answer": final["status"]}
    if final.get("status") != "valid" or not isinstance(final.get("answer"), dict):
        note = f"{coder} final.json status {final.get('status')!r} with no usable answer"
        problems.append({"pid": pid, "problem": note})
        return {"verdict": PENDING, "detail": None, "meta": meta, "note": note}
    errs = answer_mod.validate(final["answer"], lines)
    if errs:                  # a persisted "valid" answer that does not validate is malformed, never compared
        problems.append({"pid": pid, "problem": f"{coder} answer fails validation ({len(errs)} errors): {errs[0]}"[:300]})
        return {"verdict": "MALFORMED", "detail": None, "meta": meta, "note": "invalid answer", "errors": errs[:20]}
    try:
        iid = pk.get("instance_id")
        if iid not in req_cache:
            req_cache[iid] = compare.Required.from_extent(required_for(iid))
        detail = compare.compare(final["answer"], req_cache[iid]).to_dict()
    except Exception as e:   # loud: the packet stays pending and the problem is listed
        note = f"{coder} comparison failed: {type(e).__name__}: {e}"[:300]
        problems.append({"pid": pid, "problem": note})
        return {"verdict": PENDING, "detail": None, "meta": meta, "note": note}
    return {"verdict": detail["verdict"], "detail": detail, "meta": meta}


def decisions(key: dict, work, required_for, packets_dir, pair_plan=None, unseal: bool = False) -> dict:
    """The decisions record for every keyed packet. `required_for(instance_id) -> PartedExtent`.
    `packets_dir`: holds `<pid>.lines.json`, against which every answer is validated first.
    `pair_plan` (`plan.PairPlan`): each packet of the main block's plan is scored by its own pair, from its pair record. A packet of the plan
    with no pair record yet is pending (not dispatched); one the plan left uncoded has `not_coded` and no decision. Every other packet
    (set K, the pilot) is scored by `CODERS`, the `--pair`."""
    if key.get("format") != "icsa-inspection-key-v1":
        raise ValueError(f"not an inspection key: format {key.get('format')!r}")
    for w in {str(work), *[str(pk["_work"]) for pk in key["packets"].values() if pk.get("_work")]}:
        PL.require_unsealed(w, unseal)             # the main block's answers are sealed until the block is over
    req_cache: dict = {}
    problems: list[dict] = []
    out: dict[str, dict] = {}
    work_default, packets_default = work, packets_dir
    for pid in sorted(key["packets"]):
        pk = key["packets"][pid]
        work, packets_dir = pk.get("_work") or work_default, pk.get("_packets_dir") or packets_default      # a sealed packet is read where it is
        cls = pair_plan.classify(pid, pk) if pair_plan is not None else None
        pair = list(CODERS) if cls is None else (cls["pair"] if cls["kind"] == "coded" else None)
        label = pk.get("label")
        is_n = pk["set"] == "N"                       # a run with no label: answered, never scored against one
        entry = {"set": pk["set"], "phase": pk["phase"], "run_key": pk["run_key"], "instance_id": pk.get("instance_id"),
                 "option": pk.get("option"), "layout": pk.get("layout"), "model": pk.get("model"),
                 "instrument": label, "forced": bool(pk.get("forced")), "c_stratum": pk.get("c_stratum"),
                 "pair": pair, "coder_pair": PL.pair_name(pair), "in_plan": cls is not None}
        if pk["set"] == "K":
            entry.update(truth=pk.get("truth"), truth_note=pk.get("truth_note", ""),
                         truth_parts=pk.get("truth_parts", []), pattern=pk.get("pattern"),
                         k_group=pk.get("k_group") or "core", stated_narrowing=bool(pk.get("stated_narrowing", False)))
        if cls is not None:
            entry["plan_position"], entry["plan_section"] = cls["position"], cls["section"]
            if "record" in cls:       # the pair as first assigned, and whether the one permitted change happened (plan.reassign_if_quota_failed)
                entry["assigned_pair"], entry["reassigned"] = cls["record"]["assigned"]["pair"], bool(cls["record"]["reassignments"])
                entry["sonnet_subject_sol_quota_failed"] = any(n.get("event") == "sonnet_subject_sol_quota_failed" for n in cls["record"]["notes"])
                entry["sonnet_sol_exception"] = str(cls["record"]["assigned"].get("reason") or "").startswith(PL.SONNET_EXCEPTION_WHY)
        if cls is not None and cls["kind"] == "not_dispatched":
            out[pid] = {**entry, "coders": {}, "pending": ["not_dispatched"], "decision": None}
            continue
        if cls is not None and cls["kind"] == "uncoded":
            out[pid] = {**entry, "coders": {}, "pending": [], "decision": None, "not_coded": cls["reason"]}
            continue
        lines, lprob = _read_lines(packets_dir, pid)
        if lprob:
            problems.append({"pid": pid, "problem": lprob})
        coders = {c: _coder_entry(key, pid, pk, c, work, required_for, req_cache, problems, lines) for c in pair}
        if lprob:             # cannot validate: nothing may be compared
            for c in pair:
                if coders[c]["verdict"] not in (PENDING,):
                    coders[c] = {"verdict": PENDING, "detail": None, "meta": coders[c]["meta"], "note": lprob}
        pending = [c for c in pair if coders[c]["verdict"] == PENDING]
        instrument_missing = label not in decide.LABELS and not is_n
        entry.update(coders=coders, pending=pending)
        if is_n:
            entry.update(decision=None, not_scored=True, time_capped=bool(pk.get("time_capped")))
        elif pending:
            entry["decision"] = None
        else:
            used = label if not instrument_missing else "unknown"
            if instrument_missing:
                entry["instrument_missing"] = True
            a, b = pair
            entry["decision"] = decide.decide(used, coders[a]["verdict"], coders[b]["verdict"], coders[a]["detail"], coders[b]["detail"])
        out[pid] = entry
    return {"format": FORMAT_DECISIONS, "packets": out, "problems": problems}


# ----------------------------------------------------------------------------- statistics

def cp_upper(k: int, n: int, conf: float = 0.95) -> float | None:
    """Exact (Clopper-Pearson) two-sided upper bound on a rate with k events in n: the p at which P(X <= k) = (1-conf)/2.
    Science, #76, 20:12Z: beside each option's K counts, so a perfect score on 12 cases reads as bounding the error at
    about 26%, not as 0 (1 - 0.025 ** (1/12) = 0.2646)."""
    if n <= 0:
        return None
    if k >= n:
        return 1.0
    a = (1 - conf) / 2

    def cdf(pr: float) -> float:
        return sum(math.comb(n, i) * pr ** i * (1 - pr) ** (n - i) for i in range(k + 1))
    lo, hi = k / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if cdf(mid) > a:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def wilson(k: int, n: int, z: float = Z95) -> dict:
    """Wilson score interval for k of n; null bounds when n is 0."""
    if n <= 0:
        return {"k": k, "n": n, "rate": None, "lo": None, "hi": None}
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return {"k": k, "n": n, "rate": p, "lo": max(0.0, centre - half), "hi": min(1.0, centre + half)}


def cohen_kappa(pairs, cats=KAPPA_CATS) -> dict:
    """Cohen's kappa of (coder A, coder B) category pairs. Expected agreement 1 -> kappa null."""
    n = len(pairs)
    table = [[0] * len(cats) for _ in cats]
    for a, b in pairs:
        table[cats.index(a)][cats.index(b)] += 1
    out = {"n": n, "table": table, "categories": list(cats), "kappa": None, "observed": None, "expected": None}
    if n == 0:
        out["why_null"] = "no packets"
        return out
    po = sum(table[i][i] for i in range(len(cats))) / n
    rows = [sum(r) for r in table]
    cols = [sum(table[i][j] for i in range(len(cats))) for j in range(len(cats))]
    pe = sum(rows[i] * cols[i] for i in range(len(cats))) / (n * n)
    out.update(observed=po, expected=pe)
    if abs(1 - pe) < 1e-12:
        out["why_null"] = "expected agreement is 1 (both coders used a single category throughout)"
        return out
    out["kappa"] = (po - pe) / (1 - pe)
    return out


def _status(violated: bool, pending: bool, empty: bool) -> str:
    return "fail" if violated else ("incomplete" if pending or empty else "pass")


def _pc(p) -> tuple:
    """The two coders that score this packet: its own pair (the plan's), else the report's `--pair`."""
    return tuple(p.get("pair") or CODERS)


def _vs(p) -> list:
    return [p["coders"][c]["verdict"] for c in _pc(p)]


def _pair(p):
    return None if p["pending"] else decide.pair(*_vs(p))


def _kcat(v: str) -> str:
    return v if v in KAPPA_CATS else "CANNOT_TELL"      # MALFORMED counts as CANNOT_TELL


# ----------------------------------------------------------------------------- K-test parts

def _k_part1(pks: list[dict], refused: list[dict] = ()) -> dict:
    comp = [p for p in pks if p["truth"] == "complete"]
    om = [p for p in pks if p["truth"] == "omitting"]
    om_both_complete = [p for p in om if _pair(p) == "COMPLETE"]
    comp_both_complete = [p for p in comp if _pair(p) == "COMPLETE"]
    comp_both_omitting = [p for p in comp if _pair(p) == "OMITTING"]
    pend = [p for p in pks if p["pending"]]
    pend_comp = [p for p in comp if p["pending"]]
    # a refused case is an unavailable evaluation: it stays in its denominator (truth from the key)
    r_om = [r for r in refused if r.get("truth") == "omitting"]
    r_comp = [r for r in refused if r.get("truth") != "omitting"]
    n = len(comp) + len(r_comp)
    n_om = len(om) + len(r_om)
    best = (len(comp_both_complete) + len(pend_comp) + len(r_comp)) / n if n else None
    violated = bool(om_both_complete or comp_both_omitting or (n and best < 0.8))
    return {
        "status": _status(violated, bool(pend) or bool(refused), not pks and not refused or not n or not n_om),
        "refused_unavailable": len(refused),
        "omitting_cases_answered_complete_by_both": {"k": len(om_both_complete), "n": n_om, "must_be": 0,
                                                      "pids": [p["pid"] for p in om_both_complete]},
        "complete_cases_answered_complete_by_both": {"k": len(comp_both_complete), "n": n, "min_share": 0.8,
                                                      "share": len(comp_both_complete) / n if n else None},
        "complete_cases_answered_omitting_by_both": {"k": len(comp_both_omitting), "n": n, "must_be": 0,
                                                      "pids": [p["pid"] for p in comp_both_omitting]},
        "pending": [p["pid"] for p in pend]}


def _k_part2(pks: list[dict], refused: list[dict] = ()) -> dict:
    om = [p for p in pks if p["truth"] == "omitting"]
    bad = [p for p in om if p["decision"] and p["decision"]["label"] == "complete"]
    pend = [p for p in pks if p["pending"]]
    n_om = len(om) + sum(1 for r in refused if r.get("truth") == "omitting")
    return {"status": _status(bool(bad), bool(pend) or bool(refused), not n_om),
            "refused_unavailable": len(refused),
            "omitting_cases_ending_complete": {"k": len(bad), "n": n_om, "must_be": 0,
                                               "pids": [p["pid"] for p in bad]},
            "pending": [p["pid"] for p in pend]}


MATCHED_OPTIONS = ("T", "D", "M")


def _k_by_option(ks: list[dict], refused_k: list[dict]) -> dict:
    matched = [p for p in ks if p["k_group"] == "option-matched"]
    rmatched = [r for r in refused_k if (r.get("k_group") or "core") == "option-matched"]
    seen = {str(p["option"]) for p in matched} | {str(r.get("option")) for r in rmatched}
    opts = list(MATCHED_OPTIONS)          # rubric 6-7: the matched subset must be present in all three options
    ignored = sorted(seen - set(MATCHED_OPTIONS))      # names are taken as written, never normalised
    per = {}
    for o in opts:
        sub = [p for p in matched if str(p["option"]) == o]
        ro = [r for r in rmatched if str(r.get("option")) == o]
        p1, p2 = _k_part1(sub, ro), _k_part2(sub, ro)
        st = ("fail" if "fail" in (p1["status"], p2["status"])
              else "incomplete" if "incomplete" in (p1["status"], p2["status"]) else "pass")
        why = []
        if not any(p["truth"] == "complete" for p in sub) and not any(r.get("truth") != "omitting" for r in ro):
            why.append("no option-matched complete case")
        if not any(p["truth"] == "omitting" for p in sub) and not any(r.get("truth") == "omitting" for r in ro):
            why.append("no option-matched omitting case")
        per[o] = {"status": st, "n": len(sub) + len(ro), "part1": p1, "part2": p2,
                  **({"reason": "; ".join(why)} if why else {})}
    sts = [v["status"] for v in per.values()]
    status = "fail" if "fail" in sts else ("incomplete" if "incomplete" in sts else "pass")
    return {"status": status, "options": per, "ignored_options": ignored, "n_matched": len(matched), "refused_unavailable": len(rmatched)}


# ----------------------------------------------------------------------------- set C, pilot

def _c_cells(cs: list[dict], population) -> dict:
    """Set C runs per planned option x layout cell, every cell, the pilot's count and the calibration's apart (science, #76, 22:40Z).
    A cell with none is NAMED, as not tested on that cell: it never reads as passed. Part 4 itself is decided on the cells that have
    runs; when none has, it is `not_tested` (amendment 29(h)). `cs` holds the pilot's and the calibration's set C packets, as rubric §1
    registers set C; `set_c_pilot` and `set_c_calibration` are given apart."""
    if population is None:
        return {"checked": False, "cells": None, "cells_without_set_c": None, "n_cells_without_set_c": None,
                "note": "no population given: the planned option x layout cells were not checked for set C runs"}
    planned = {ph: Counter((str(r.get("option")), str(r.get("layout"))) for r in population if r.get("phase") == ph)
               for ph in ("pilot", "calibration")}
    have = {ph: Counter((str(p["option"]), str(p["layout"])) for p in cs if p["phase"] == ph) for ph in ("pilot", "calibration")}
    keys = sorted(set(planned["pilot"]) | set(planned["calibration"]))
    cells = {f"{o}|{l}": {"planned_pilot": planned["pilot"][(o, l)], "planned_calibration": planned["calibration"][(o, l)],
                          "set_c_pilot": have["pilot"][(o, l)], "set_c_calibration": have["calibration"][(o, l)],
                          "set_c_runs": have["pilot"][(o, l)] + have["calibration"][(o, l)]} for o, l in keys}
    none = [c for c, v in cells.items() if v["set_c_runs"] == 0]
    return {"checked": True, "cells": cells, "cells_without_set_c": none, "n_cells_without_set_c": len(none), "n_cells": len(cells),
            "note": "set C runs per planned option x layout cell, the pilot's and the calibration's apart; a cell without any is not tested "
                    "on that cell, which is a gap in the gate and never a pass"}


def _c_pilot(cs: list[dict], investigations, refused: list[dict] = (), population=None) -> dict:
    pend = [p for p in cs if p["pending"]]
    done = [p for p in cs if not p["pending"]]
    fc = [p for p in done if _pair(p) == "COMPLETE" and p["instrument"] == "omitting"]
    fo = [p for p in done if _pair(p) == "OMITTING" and p["instrument"] == "complete"]
    # a refused run is an unavailable evaluation: it stays in the denominators with its instrument label
    n_ic = sum(1 for p in cs if p["instrument"] == "complete") + sum(1 for r in refused if r.get("label") == "complete")
    n_io = sum(1 for p in cs if p["instrument"] == "omitting") + sum(1 for r in refused if r.get("label") == "omitting")
    unavailable = len(refused)
    dis = []
    for p in done:
        pr = _pair(p)
        contradicts = (pr == "COMPLETE" and p["instrument"] == "omitting") or (
            pr == "OMITTING" and p["instrument"] == "complete")
        v = _vs(p)
        split = v[0] != v[1] or "MALFORMED" in v
        if contradicts or split:
            dis.append({"pid": p["pid"], "run_key": p["run_key"], "instrument": p["instrument"], "coders": v,
                        "kind": ("pair contradicts instrument" if contradicts else "coders disagree"),
                        "note": (investigations or {}).get(p["pid"])})
    uninvestigated = [d["pid"] for d in dis if not d["note"]]
    violated = bool(fc) or 10 * len(fo) > n_ic
    # science, #76, 23:31Z: decided on pilot and calibration together, with the pilot's own figures beside. The zero-tolerance limit
    # means a pilot failure still fails the pool; the pilot's share of false OMITTING is shown, never decided on alone.
    pil = [p for p in cs if p.get("phase") == "pilot"]
    pil_done = [p for p in pil if not p["pending"]]
    pil_ic = sum(1 for p in pil if p["instrument"] == "complete") + sum(1 for r in refused if r.get("label") == "complete" and r.get("phase") == "pilot")
    pil_io = sum(1 for p in pil if p["instrument"] == "omitting") + sum(1 for r in refused if r.get("label") == "omitting" and r.get("phase") == "pilot")
    pil_fo = sum(1 for p in pil_done if _pair(p) == "OMITTING" and p["instrument"] == "complete")
    pilot_only = {"n_runs": len(pil), "answered_complete_by_both_while_instrument_omitting":
                  {"k": sum(1 for p in pil_done if _pair(p) == "COMPLETE" and p["instrument"] == "omitting"), "n": pil_io},
                  "answered_omitting_by_both_while_instrument_complete": {"k": pil_fo, "n": pil_ic, "share": pil_fo / pil_ic if pil_ic else None}}
    cells = _c_cells(cs, population)
    # Amendment 29(h): the pilot ran and no cell has a set C run: part 4 is NOT TESTED, go rests on the other parts, and that is stated. It
    # is never a pass. It takes planned runs to know this: with no population, or none planned, the pilot hasn't happened, and part 4 is incomplete.
    nothing_to_test = not cs and not refused and bool(cells.get("checked")) and bool(cells.get("cells"))
    incomplete = bool(pend) or (not cs and not refused) or bool(uninvestigated) or unavailable > 0
    return {
        "status": "not_tested" if nothing_to_test else _status(violated, incomplete, False),
        "set_c_cells": cells, "cells_without_set_c": cells["cells_without_set_c"],
        "decided_on": "the set C runs of the pilot and the calibration together (science, #76, 23:31Z), the pilot's own figures beside",
        "pilot_only": pilot_only,
        "answered_complete_by_both_while_instrument_omitting": {"k": len(fc), "n": n_io, "must_be": 0, "pids": [p["pid"] for p in fc]},
        "answered_omitting_by_both_while_instrument_complete": {"k": len(fo), "n": n_ic, "max_share": 0.1,
                                                                 "share": len(fo) / n_ic if n_ic else None,
                                                                 "pids": [p["pid"] for p in fo]},
        "disagreements": dis,
        "pending_investigation": uninvestigated,
        "investigations_given": investigations is not None,
        "pending": [p["pid"] for p in pend], "n_runs": len(cs) + unavailable, "refused_unavailable": unavailable}


# ----------------------------------------------------------------------------- pilot unknown share

def _final_label(p) -> str | None:
    """The label after inspection; None while pending."""
    return None if p["pending"] else p["decision"]["label"]


def _planned_runs(decs: dict, key: dict, population, phase: str) -> tuple[list[dict], str]:
    """One record per PLANNED run of the phase: {run_key, label (the instrument's, None for a time-capped run), unlabelled,
    time_capped, packet (its set R or C decision entry, else None), refused}. From the population when it is given; else from the keyed
    runs only. A set N packet or refused set N run is the run itself, never a second record."""
    by_run = {p["run_key"]: p for p in decs.values()}
    refused = {r["run_key"]: r for r in key.get("refused", []) if r.get("phase") == phase}
    runs = []
    if population is not None:
        for r in population:
            if r.get("phase") != phase:
                continue
            p = by_run.get(r["run_key"])
            runs.append({"run_key": r["run_key"], "label": r.get("label"), "unlabelled": bool(r.get("unlabelled")),
                         "time_capped": bool(r.get("time_capped")), "packet": p if p is not None and p["set"] in ("R", "C") else None,
                         "refused": r["run_key"] in refused})
        return runs, "population"
    for p in decs.values():
        if p["phase"] == phase and p["set"] in ("R", "C", "N"):
            runs.append({"run_key": p["run_key"], "label": p["instrument"], "unlabelled": p["set"] == "N",
                         "time_capped": bool(p.get("time_capped")), "packet": p if p["set"] in ("R", "C") else None, "refused": False})
    for rk, r in refused.items():
        runs.append({"run_key": rk, "label": r.get("label"), "unlabelled": r.get("set") == "N", "time_capped": bool(r.get("time_capped")),
                     "packet": None, "refused": True})
    for u in key.get("unlabelled", []):                # an unlabelled run of another phase is in no set: the key lists it
        if u.get("phase") == phase and u.get("set") is None:
            runs.append({"run_key": u["run_key"], "label": None, "unlabelled": True, "time_capped": bool(u.get("time_capped")),
                         "packet": None, "refused": False})
    return runs, "keyed runs only (no population given): the denominator is the keyed pilot runs"


def _pilot_unknown(decs: dict, key: dict, population, phase: str) -> dict:
    """The phase's share of planned runs left unknown (science, #76, 22:28Z).

    share = (runs `unknown` after inspection + runs left without a label for any reason OTHER than the time cap) / (planned runs - time-capped runs).
    A harness or infrastructure loss, a turn or token cap, a run that never started: all in the numerator and the denominator. A run
    ended by the time cap made no claim: in neither, and reported beside the share as `time_capped` (K in report-spec). A refused
    packet has no coder evaluation that could resolve it: a refused run the instrument left unknown stays unknown for certain. Only a
    PENDING set R run is uncertain: resolved in the best case, still unknown in the worst. A set N answer is not read at all."""
    runs, basis = _planned_runs(decs, key, population, phase)
    capped = [x for x in runs if x["time_capped"]]
    counted = [x for x in runs if not x["time_capped"]]
    labels, pending, refused_unknown, unlabelled = {}, [], [], []
    for x in counted:
        rk, p = x["run_key"], x["packet"]
        if x["unlabelled"]:                  # no label, not for the time cap: unknown for certain, whatever the coders said of its code
            unlabelled.append(rk)
            labels[rk] = "unknown"
        elif p is None:
            labels[rk] = x["label"]
            if x["refused"] and x["label"] == "unknown":
                refused_unknown.append(rk)
        elif p["pending"]:
            labels[rk] = p["instrument"]
            if p["instrument"] == "unknown":
                pending.append(rk)
        else:
            labels[rk] = _final_label(p)
    n = len(counted)
    unk = sum(1 for rk, v in labels.items() if v == "unknown" and rk not in pending)    # refused and unlabelled included
    bad = sum(1 for v in labels.values() if v not in decide.LABELS)
    k, planned = len(capped), len(runs)
    return {"basis": basis, "n_runs": n, "planned_runs": planned,
            "unknown": {"k": unk, "n": n, "max_share": 0.1, "share": unk / n if n else None,
                        "refused_unknown": len(refused_unknown)},
            "time_capped": {"k": k, "planned": planned, "share": k / planned if planned else None, "max_share": 0.1,
                            "over_10_percent": bool(planned and 10 * k > planned), "runs": sorted(x["run_key"] for x in capped),
                            "note": "K (runs ended by the time cap): out of the share; reported beside it, never a part-5 failure"},
            "pending": sorted(pending), "refused_unknown": sorted(refused_unknown), "unlabelled_unknown": sorted(unlabelled),
            "best_case_share": unk / n if n else None,
            "worst_case_share": (unk + len(pending)) / n if n else None, "no_label": bad}


def _part5(decs, key, population) -> dict:
    pil = _pilot_unknown(decs, key, population, "pilot")
    cal = _pilot_unknown(decs, key, population, "calibration")
    k, n = pil["unknown"]["k"], pil["n_runs"]
    violated = bool(n and 10 * k > n)
    return {"status": _status(violated, bool(pil["pending"]) or pil["no_label"] > 0, n == 0),
            **pil, "calibration_information_only": cal}


def _set_n(ns: list[dict], refused_n: list[dict]) -> dict:
    """What the coders answered on the pilot's unlabelled runs. Never scored: there is no label to score it against."""
    out = {"not_scored": True,
           "note": "pilot runs with no label (K, the runs ended by the time cap, and every other unlabelled run): read like any packet, "
                   "answered, and not scored against a label; no part, share, kappa or coverage record reads them",
           "packets": len(ns), "refused": len(refused_n), "time_capped_packets": sum(1 for p in ns if p.get("time_capped")),
           "refused_reasons": [{"run_key": r.get("run_key"), "reason": r.get("reason")} for r in refused_n], "by_coder": {}}
    for c in CODERS:
        cnt = Counter(p["coders"][c]["verdict"] for p in ns)
        out["by_coder"][c] = {"answered": len(ns) - cnt[PENDING], "pending": cnt[PENDING],
                              **{v: cnt[v] for v in ("COMPLETE", "OMITTING", "CANNOT_TELL", "MALFORMED")}}
    return out


# ----------------------------------------------------------------------------- reporting (§8)

def _group_kappa(ps: list[dict], field) -> dict:
    out = {}
    for g in sorted({str(p[field]) for p in ps}):
        out[g] = cohen_kappa([(_kcat(_vs(p)[0]), _kcat(_vs(p)[1])) for p in ps if str(p[field]) == g])
    return out


def _kappas(real: list[dict], ks: list[dict]) -> dict:
    real = [p for p in real if not p["pending"]]
    ks = [p for p in ks if not p["pending"]]
    pair_of = lambda p: (_kcat(_vs(p)[0]), _kcat(_vs(p)[1]))      # noqa: E731
    return {"note": "categories COMPLETE/OMITTING/CANNOT_TELL; MALFORMED counted as CANNOT_TELL; "
                    "real runs = sets R and C; pending packets excluded",
            "real_overall": cohen_kappa([pair_of(p) for p in real]),
            "real_by_option": _group_kappa(real, "option"), "real_by_model": _group_kappa(real, "model"),
            "k_overall": cohen_kappa([pair_of(p) for p in ks])}


def _accuracy(ks: list[dict]) -> dict:
    out = {}
    for c in CODERS:
        cnt = Counter()
        for p in ks:
            v = p["coders"][c]["verdict"]
            t = p["truth"].upper()
            if v == PENDING:
                cnt["pending"] += 1
            elif v == "MALFORMED":
                cnt["malformed"] += 1
            elif v == "CANNOT_TELL":
                cnt["cannot_tell"] += 1
            elif v == t:
                cnt["correct"] += 1
            else:
                cnt["wrong"] += 1
        out[c] = {"correct": {"k": cnt["correct"], "n": len(ks)}, "wrong": cnt["wrong"],
                  "cannot_tell": cnt["cannot_tell"], "malformed": cnt["malformed"], "pending": cnt["pending"]}
        by = {}
        for o in sorted({p.get("option") for p in ks}, key=str):
            sub = [p for p in ks if p.get("option") == o]
            v = [p["coders"][c]["verdict"] for p in sub]
            wrong = sum(1 for x, p in zip(v, sub) if x in ("COMPLETE", "OMITTING") and x != p["truth"].upper())
            correct = sum(1 for x, p in zip(v, sub) if x == p["truth"].upper())
            decided = sum(1 for x in v if x != PENDING)
            by[str(o)] = {"n": len(sub), "correct": correct, "wrong": wrong, "not_correct": decided - correct,
                          "pending": len(sub) - decided,
                          "wrong_upper95": cp_upper(wrong, decided), "not_correct_upper95": cp_upper(decided - correct, decided)}
        out[c]["by_option"] = by
        # an omitting case whose extraction names more parts than the truth: registered, it blocks the coders' coverage
        sup = []
        for p in ks:
            det = (p["coders"][c] or {}).get("detail") or {}
            if p["truth"] == "omitting" and det.get("groups") is not None and p.get("truth_parts"):
                got = {tuple(g) for g in det["groups"]}
                want = {tuple(t) for t in p["truth_parts"]}
                if got > want:
                    sup.append({"pid": p["pid"], "truth_parts": sorted({t[0] for t in want}), "named_parts": sorted({g[0] for g in got})})
        out[c]["superset_extractions"] = len(sup)
        out[c]["superset_answers"] = sup      # science, #76, 23:58Z: listed. K is left as it is: truth is never taken from a coder, and section 7 scores no parts
    return out


def _k_stated_narrowing(ks: list[dict]) -> dict:
    """Descriptive, beside the gate and never part of it. An omitting case tagged `stated_narrowing` openly says, in a comment, a print
    or its report text, that less data is used. Each coder's accuracy with and without those cases, so a score cannot lean on them unnoticed."""
    om = [p for p in ks if p["truth"] == "omitting"]
    tagged = [p for p in om if p.get("stated_narrowing")]
    groups = {}
    for g in sorted({p.get("k_group") or "core" for p in om}):
        sub = [p for p in om if (p.get("k_group") or "core") == g]
        groups[g] = {"omitting": len(sub), "tagged": sum(1 for p in sub if p.get("stated_narrowing"))}
    return {"omitting": len(om), "tagged": len(tagged), "share_of_omitting": len(tagged) / len(om) if om else None, "by_group": groups,
            "all_cases": {"with": _accuracy(ks), "without": _accuracy([p for p in ks if not p.get("stated_narrowing")])},
            "omitting_cases": {"with": _accuracy(om), "without": _accuracy([p for p in om if not p.get("stated_narrowing")])}}


def _k_omitting_unstated(ks: list[dict]) -> dict:
    """Science, #76, 23:58Z: the number it reads. The omitting cases that don't say they use less data, so only the code can give them away:
    the pair's outcome on them, per pair, with an exact bound. A case the pair doesn't answer OMITTING by both is counted as missed."""
    def one(ps):
        done = [p for p in ps if not p["pending"]]
        both_o = sum(1 for p in done if _pair(p) == "OMITTING")
        both_c = sum(1 for p in done if _pair(p) == "COMPLETE")
        missed = len(done) - both_o
        return {"n": len(ps), "both_omitting": both_o, "both_complete": both_c, "not_both_omitting": missed, "pending": len(ps) - len(done),
                "both_complete_upper95": cp_upper(both_c, len(done)), "not_both_omitting_upper95": cp_upper(missed, len(done))}
    un = [p for p in ks if p["truth"] == "omitting" and not p.get("stated_narrowing")]
    return {"pair": list(CODERS), **one(un), "by_option": {str(o): one([p for p in un if p.get("option") == o]) for o in sorted({p.get("option") for p in un}, key=str)}}


def _resolved_share(rs: list[dict], refused_r: list[dict] = ()) -> dict:
    """Resolved / all set R packets. A refused R packet counts as unresolved, in the denominator, and is shown."""
    def one(ps, rr):
        return {"resolved": sum(1 for p in ps if p["decision"] and p["decision"]["route"] == "inspection"),
                "n": len(ps) + len(rr), "pending": sum(1 for p in ps if p["pending"]), "refused": len(rr)}
    opts = sorted({str(p["option"]) for p in rs} | {str(r.get("option")) for r in refused_r})
    mods = sorted({str(p["model"]) for p in rs} | {str(r.get("model")) for r in refused_r})
    return {"overall": one(rs, refused_r),
            "by_option": {o: one([p for p in rs if str(p["option"]) == o], [r for r in refused_r if str(r.get("option")) == o]) for o in opts},
            "by_model": {m: one([p for p in rs if str(p["model"]) == m], [r for r in refused_r if str(r.get("model")) == m]) for m in mods}}


def _c_cell(ps):
    done = [p for p in ps if not p["pending"]]
    om = [p for p in done if p["instrument"] == "omitting"]
    co = [p for p in done if p["instrument"] == "complete"]
    return {"false_complete": wilson(sum(1 for p in om if _pair(p) == "COMPLETE"), len(om)),
            "false_omitting": wilson(sum(1 for p in co if _pair(p) == "OMITTING"), len(co)),
            "pending": len(ps) - len(done)}


def _c_grouped(ps):
    return {f"{o}|{l}": _c_cell([p for p in ps if (str(p["option"]), str(p["layout"])) == (o, l)])
            for o, l in sorted({(str(p["option"]), str(p["layout"])) for p in ps})}


def _c_by_model(ps):
    return {m: _c_cell([p for p in ps if str(p["model"]) == m]) for m in sorted({str(p["model"]) for p in ps})}


def _c_rates(cs: list[dict], strata: list[dict]) -> dict:
    grouped, by_model = _c_grouped, _c_by_model
    pil = [p for p in cs if p["phase"] in ("pilot", "calibration")]
    main = [p for p in cs if p["phase"] in MAIN_PHASES]      # the pagination cell is sampled by main's rule, so it is read as main
    weights = {(s["option"], s["layout"], s["label"]): s for s in strata}
    rew: dict = {}
    # the cells come from the strata as well as from the sampled packets: under the hash rule a stratum can have runs (N > 0) and no sampled run (n = 0),
    # and it must stay in the cells and be counted as not estimable, not vanish with the packets
    cells = sorted({(str(p["option"]), str(p["layout"])) for p in main} | {(str(s["option"]), str(s["layout"])) for s in strata})
    for (o, l) in cells:
        row = {}
        for field, label, verdict in (("false_complete", "omitting", "COMPLETE"), ("false_omitting", "complete", "OMITTING")):
            s = weights.get((o, l, label))
            ps = [p for p in main if (str(p["option"]), str(p["layout"])) == (o, l) and p["instrument"] == label
                  and p.get("c_stratum") and not p["pending"]]
            k = sum(1 for p in ps if _pair(p) == verdict)
            row[field] = ({"k": k, "n": len(ps), "N": s["N"], "est_k_in_N": (s["N"] * k / len(ps)) if ps else None,
                           "rate": k / len(ps) if ps else None, "not_estimable": not ps} if s else None)
        rew[f"{o}|{l}"] = row
    tot: dict = {}
    for field in ("false_complete", "false_omitting"):
        est = sum(r[field]["est_k_in_N"] for r in rew.values() if r[field] and r[field]["est_k_in_N"] is not None)
        N = sum(r[field]["N"] for r in rew.values() if r[field] and r[field]["est_k_in_N"] is not None)
        tot[field] = {"est_k": est, "N": N, "rate": est / N if N else None}
    gap = {f: sum(r[f]["N"] for r in rew.values() if r[f] and r[f]["est_k_in_N"] is None) for f in ("false_complete", "false_omitting")}
    return {"pilot_and_calibration_raw": grouped(pil), "main_raw": grouped(main),
            "pilot_and_calibration_by_model": by_model(pil), "main_by_model": by_model(main),
            "main_reweighted": {"note": "each option x layout x label stratum weighted N/n (sampled n of N runs); "
                                        "est_k_in_N = N*k/n; forced runs excluded; no interval (the weights make "
                                        "Wilson inapplicable)",
                                "cells": rew, "total": tot,
                                "not_estimable_N": gap},          # runs of strata with no sampled run: in no cell estimate and not in the total's N
            "wilson_z": Z95}


def _route_mix(decs: dict, key: dict, population) -> dict:
    if population is None:
        return {"omitted": "no population given: the route mix needs every run, not only the queued ones"}
    by_run = {p["run_key"]: p for p in decs.values()}
    refused = {r["run_key"] for r in key.get("refused", [])}

    def route(r):
        if r.get("unlabelled"):
            return "unlabelled"             # no label: a set N packet (answered, not scored), refused, or in no set
        if r.get("label") in ("complete", "omitting"):
            return "instrument"
        p = by_run.get(r["run_key"])
        if p is None:
            return "refused" if r["run_key"] in refused else "not_queued"
        if p.get("not_coded"):
            return "not_coded"            # a Sonnet subject run the plan left uncoded: its unknown stands
        if p["pending"]:
            return "pending"
        return p["decision"]["route"]
    rows = [r for r in population if r.get("phase") != "ktest"]
    def mix(rs):
        c = Counter(route(r) for r in rs)
        return {"n": len(rs), **{k: c[k] for k in ("instrument", "inspection", "unresolved", "pending", "refused", "not_queued", "unlabelled",
                                                    "not_coded")}}
    return {"overall": mix(rows),
            "by_option": {o: mix([r for r in rows if str(r.get("option")) == o]) for o in sorted({str(r.get("option")) for r in rows})},
            "by_model": {m: mix([r for r in rows if str(r.get("model")) == m]) for m in sorted({str(r.get("model")) for r in rows})}}


LIMITATIONS = [
    "models judging model-written code",
    "coders cannot be blind to the option",
    "set C skews towards vectorised code, so it measures the coders on the easier part of the population",
    "the extraction relies on reading code, not executing it",
    "Claude Opus 5.5 shares a vendor with two subject models (site_i, site_j); "
    "agreement is reported per subject model",
]
INDEPENDENT_CHECK = {"status": "not built",
                     "note": "the replay dependence test (rubric §8) is built during the campaign; "
                             "until then this is a stated limitation"}


def _k_rates(ks: list[dict]) -> dict:
    def one(ps):
        done = [p for p in ps if not p["pending"]]
        om = [p for p in done if p["truth"] == "omitting"]
        co = [p for p in done if p["truth"] == "complete"]
        return {"false_complete": wilson(sum(1 for p in om if _pair(p) == "COMPLETE"), len(om)),
                "false_omitting": wilson(sum(1 for p in co if _pair(p) == "OMITTING"), len(co)),
                "pending": len(ps) - len(done)}
    return {"note": "coder pair against truth; false-complete: pair COMPLETE among omitting cases; "
                    "false-omitting: pair OMITTING among complete cases; Wilson 95%",
            "overall": one(ks),
            "by_option": {o: one([p for p in ks if str(p["option"]) == o]) for o in sorted({str(p["option"]) for p in ks})}}


def _tokens_by(real: list[dict], field: str, coders=None) -> dict:
    out = {}
    for g in sorted({str(p[field]) for p in real}):
        row = {}
        for c in (coders or CODERS):
            ms = [p["coders"][c]["meta"] for p in real if str(p[field]) == g and p["coders"][c]["meta"] is not None]
            costs = [m["cost_usd"] for m in ms if m["cost_usd"] is not None]
            row[c] = {"n": len(ms),
                      "tokens": {k: sum((m["usage"].get(k) or 0) for m in ms)
                                 for k in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens")},
                      "wall_s": sum(m["wall_s"] for m in ms if m["wall_s"] is not None),
                      "cost_usd": {"total": sum(costs), "n": len(costs), "n_null": len(ms) - len(costs)}}
        out[g] = row
    return out


SUBAGENT_RATE_TO_SCIENCE = 0.20     # science, #76, 2 Nov 12:43Z: a coder above about this on K comes to science before the pilot's packets


def _subagents(packets: dict) -> dict:
    """Per coder, the share of packets where a subagent ran in any attempt. A coder is blind and alone, and nothing turns the tool off (coders.py), so this is reported. An
    answer archived before the count existed is `not_recorded`, in neither side of the rate."""
    sets = {"K": lambda p: p["set"] == "K", "pilot": lambda p: p["set"] == "C" and p["phase"] in ("pilot", "calibration"), "all": lambda p: True}
    out = {}
    for c in CODERS:
        by = {}
        for name, keep in sets.items():
            ms = [p["coders"][c]["meta"] for p in packets.values() if p["coders"][c]["meta"] is not None and keep(p)]
            known = [m for m in ms if m.get("subagent_attempts") is not None]
            k = sum(1 for m in known if m["subagent_attempts"])
            by[name] = {"packets": len(known), "with_subagent": k, "rate": k / len(known) if known else None,
                        "subagent_attempts": sum(m["subagent_attempts"] for m in known), "not_recorded": len(ms) - len(known)}
        out[c] = by
    high = [c for c in CODERS if out[c]["K"]["rate"] is not None and out[c]["K"]["rate"] > SUBAGENT_RATE_TO_SCIENCE]
    return {"by_coder": out, "k_rate_to_science": SUBAGENT_RATE_TO_SCIENCE, "to_science_before_the_pilot": high}


def _tokens(decs: dict, coders=None, sets=("R", "C", "K", "N", "all")) -> dict:
    out = {}
    for c in (coders or CODERS):
        by_set = {}
        for s in sets:
            ms = [p["coders"][c]["meta"] for p in decs.values()
                  if p["coders"][c]["meta"] is not None and (s == "all" or p["set"] == s)]
            if not ms:
                by_set[s] = {"n": 0}
                continue
            tok = {k: sum((m["usage"].get(k) or 0) for m in ms)
                   for k in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens")}
            walls = [m["wall_s"] for m in ms if m["wall_s"] is not None]
            costs = [m["cost_usd"] for m in ms if m["cost_usd"] is not None]
            by_set[s] = {"n": len(ms), "tokens": tok,
                         "wall_s": {"total": sum(walls), "mean": statistics.mean(walls), "median": statistics.median(walls),
                                    "n": len(walls)} if walls else None,
                         "cost_usd": {"total": sum(costs), "mean": statistics.mean(costs), "median": statistics.median(costs),
                                      "n": len(costs), "n_null": len(ms) - len(costs)} if costs else {"n": 0, "n_null": len(ms)},
                         "attempts": sum((m["attempts"] or 0) for m in ms),
                         "retried_attempts": sum(max(0, (m["attempts"] or 1) - 1) for m in ms),
                         "contaminated_attempts": sum((m["contaminated_attempts"] or 0) for m in ms)}
        out[c] = by_set
    return out


def project(report: dict, packets: dict) -> dict:
    """Linear projection: measured mean per packet x the packet counts, per coder and in total.

    The mean is over the coder's measured real-run packets (sets R and C; set K when no real packet
    is measured yet). Cost is null for a coder with no recorded cost."""
    out = {"note": "linear projection from the measured mean per packet (sets R and C where measured, else K); "
                   "coder wall time is the sum of per-packet times, i.e. sequential",
           "packets": dict(packets), "coders": {}, "total": {}}
    for c in CODERS:
        tk = report["tokens"][c]
        real = [tk[s] for s in ("R", "C") if tk[s]["n"]]
        src, basis = (real, "R+C") if real else ([tk["K"]] if tk["K"]["n"] else [], "K")
        n = sum(s["n"] for s in src)
        wall_n = sum((s["wall_s"] or {"n": 0})["n"] for s in src)
        cost_n = sum(s["cost_usd"].get("n", 0) for s in src)
        wall_mean = sum(s["wall_s"]["total"] for s in src if s["wall_s"]) / wall_n if wall_n else None
        cost_mean = sum(s["cost_usd"]["total"] for s in src if s["cost_usd"].get("n")) / cost_n if cost_n else None
        row = {"basis": basis, "measured_packets": n, "mean_wall_s": wall_mean, "mean_cost_usd": cost_mean, "phases": {}}
        for ph, cnt in packets.items():
            row["phases"][ph] = {"packets": cnt, "wall_s": wall_mean * cnt if wall_mean is not None else None,
                                 "cost_usd": cost_mean * cnt if cost_mean is not None else None}
        out["coders"][c] = row
    for ph, cnt in packets.items():
        w = [out["coders"][c]["phases"][ph]["wall_s"] for c in CODERS]
        k = [out["coders"][c]["phases"][ph]["cost_usd"] for c in CODERS]
        out["total"][ph] = {"packets": cnt, "wall_s": sum(w) if None not in w else None,
                            "cost_usd": sum(k) if None not in k else None}
    return out


# ----------------------------------------------------------------------------- the main block, per coder pair (amendment 26)

PLAN_PAIRS = (PL.SOL_PAIR, PL.FALLBACK_PAIR)


def _cell_of(p) -> str:
    return f"{p['option']}|{p['layout']}|{p['model']}"


def _pair_block(ps: list[dict], pair: tuple) -> dict:
    """Every main-block table for the packets one pair scored. No figure here is pooled with another pair's."""
    rs = [p for p in ps if p["set"] == "R"]
    cs = [p for p in ps if p["set"] == "C"]
    real = [p for p in rs + cs if not p["pending"]]
    by_id = {p["pid"]: p for p in ps}
    cats = lambda q: (_kcat(_vs(q)[0]), _kcat(_vs(q)[1]))        # noqa: E731
    return {"pair": list(pair), "coder_pair": PL.pair_name(pair),
            "packets": {"R": len(rs), "C": len(cs), "pending": sum(1 for p in ps if p["pending"]),
                        "by_cell": dict(sorted(Counter(_cell_of(p) for p in ps).items()))},
            "kappa": {"note": "categories COMPLETE/OMITTING/CANNOT_TELL; MALFORMED counted as CANNOT_TELL; this pair's R and C packets; "
                              "pending excluded",
                      "real_overall": cohen_kappa([cats(p) for p in real]),
                      "real_by_option": _group_kappa(real, "option"), "real_by_model": _group_kappa(real, "model")},
            "resolved_share": _resolved_share(rs),
            "coder_pair_on_c": {"note": "this pair's set C packets, raw Wilson 95% intervals. Not reweighted by stratum: a pair coded a subset "
                                        "of the runs that depends on the model (Sonnet first) and on the quota, so N/n from the sampling "
                                        "strata would not describe it",
                                "main_raw": _c_grouped(cs), "main_by_model": _c_by_model(cs)},
            "tokens": _tokens(by_id, pair, sets=("R", "C", "all")),
            "tokens_by_option": _tokens_by(real, "option", pair), "tokens_by_model": _tokens_by(real, "model", pair)}


def _sensitivity_sol_only(plan_ps: list[dict], refused_r: list[dict] = ()) -> dict:
    """The analysis with the Sol-coded runs' inspection only (science, amendment 26): a run another pair coded, or left uncoded or not yet
    dispatched, counts as not inspected, so it stays `unknown`. The denominator is every planned set R run: the set R packets of the plan and `refused_r`, the
    set R runs with no packet (the coding cutoff, or a refusal), which are in the key's `refused` and never among the packets."""
    sol = {p["pid"] for p in plan_ps if p.get("pair") == list(PL.SOL_PAIR)}
    rs = [p for p in plan_ps if p["set"] == "R"]
    runs = [*rs, *refused_r]

    def resolved(ps):
        return [p for p in ps if p["pid"] in sol and not p["pending"] and p["decision"] and p["decision"]["route"] == "inspection"]
    opts = sorted({str(p["option"]) for p in runs})
    mods = sorted({str(p["model"]) for p in runs})
    res = resolved(rs)
    return {"note": "Sol-coded runs only: Opus + Sonnet-coded, uncoded, not-yet-dispatched and no-packet set R runs stay as the instrument left them (unknown). "
                    "The other tables' Sol + Opus row is the same runs scored by their own pair.",
            "resolved_share": {"resolved": len(res), "n": len(runs), "sol_coded_r_packets": sum(1 for p in rs if p["pid"] in sol)},
            "labels_after_inspection": {"complete": sum(1 for p in res if p["decision"]["label"] == "complete"),
                                        "omitting": sum(1 for p in res if p["decision"]["label"] == "omitting"),
                                        "unknown": len(runs) - len(res)},
            "by_option": {o: {"resolved": len(resolved([p for p in rs if str(p["option"]) == o])),
                              "n": sum(1 for p in runs if str(p["option"]) == o)} for o in opts},
            "by_model": {m: {"resolved": len(resolved([p for p in rs if str(p["model"]) == m])),
                             "n": sum(1 for p in runs if str(p["model"]) == m)} for m in mods}}


def _main_by_pair(plan_ps: list[dict], key: dict, pair_plan) -> dict:
    """The main block's report: counts per pair, how far Sol got, the gate, the uncoded Sonnet runs, one block of tables per pair and the Sol-only
    sensitivity. Every figure is keyed by pair; there is no rate over the pairs together."""
    plan = pair_plan.plan
    by_pair = {PL.pair_name(pr): _pair_block([p for p in plan_ps if p.get("pair") == list(pr)], pr) for pr in PLAN_PAIRS}
    stray = [p["pid"] for p in plan_ps if p.get("pair") not in (None, *[list(x) for x in PLAN_PAIRS])]
    if stray:
        raise PL.PairError(f"packets with a pair the plan does not use: {stray[:5]}")
    uncoded = [p for p in plan_ps if p.get("not_coded")]
    undispatched = [p for p in plan_ps if p.get("pair") is None and not p.get("not_coded")]
    planned_cells = Counter(i["stratum"] for i in plan["order"])
    cells = {}
    for c in sorted(planned_cells):
        mine = [p for p in plan_ps if _cell_of(p) == c]
        cells[c] = {"planned": planned_cells[c], "packets": len(mine),
                    **{PL.pair_name(pr): sum(1 for p in mine if p.get("pair") == list(pr)) for pr in PLAN_PAIRS},
                    "not_coded": sum(1 for p in mine if p.get("not_coded")),
                    "not_dispatched": sum(1 for p in mine if p.get("pair") is None and not p.get("not_coded")),
                    "no_packet": planned_cells[c] - len(mine)}
    assigned_sol = [p for p in plan_ps if p.get("assigned_pair") == list(PL.SOL_PAIR)]
    assigned_fb = [p for p in plan_ps if p.get("assigned_pair") == list(PL.FALLBACK_PAIR)]
    sol_state = {"assigned_sol": len(assigned_sol), "coded_by_sol_now": by_pair["sol+opus"]["packets"]["R"] + by_pair["sol+opus"]["packets"]["C"],
                 "reassigned_to_opus_sonnet": sum(1 for p in plan_ps if p.get("reassigned")),
                 "last_sol_position": max((p["plan_position"] for p in assigned_sol), default=None),
                 "first_fallback_position": min((p["plan_position"] for p in assigned_fb), default=None),
                 "order_length": len(plan["order"]),
                 "sonnet_subject_sol_quota_failed": sorted(p["run_key"] for p in plan_ps if p.get("sonnet_subject_sol_quota_failed")),
                 # science, #34, 4 Nov 20:22Z: Sonnet subject runs coded by Sol + Opus after the gate closed at 95 (hard stop 99, in the gate below)
                 "sonnet_subject_sol_past_threshold": sum(1 for p in plan_ps if p.get("sonnet_sol_exception"))}
    gate = pair_plan.gate_snapshot()
    return {"note": "amendment 26: each packet is scored by its own pair; no figure below is pooled across pairs",
            "plan": {"plan_sha256": plan["plan_sha256"], "order_sha256": plan["order_sha256"], "seed": plan["seed"],
                     "blocks": plan["blocks"], "n_planned": plan["n_planned"], "sections": plan["sections"]},
            "coded_packets": key.get("coded_packets"), "coded_unused": key.get("coded_unused"),
            "packets": len(plan_ps), "runs_per_pair": {**{n: sum(b["packets"][s] for s in ("R", "C")) for n, b in by_pair.items()},
                                                      "not_coded": len(uncoded), "not_dispatched": len(undispatched)},
            "by_cell": cells, "sol": sol_state, "gate": gate,
            "not_coded": {"n": len(uncoded), "alarm": bool(uncoded),
                          "note": "Sonnet subject runs left waiting for Sol (the gate was not open when the pass ended): never Opus + Sonnet, so their "
                                  "unknown stands unless a later pass codes them" if uncoded else "none",
                          "by_reason": dict(sorted(Counter(str(p["not_coded"]) for p in uncoded).items())),
                          "by_cell": dict(sorted(Counter(_cell_of(p) for p in uncoded).items())),
                          "runs": sorted(({"run_key": p["run_key"], "set": p["set"], "option": p["option"], "layout": p["layout"],
                                           "model": p["model"], "reason": p["not_coded"]} for p in uncoded), key=lambda r: r["run_key"])},
            "by_pair": by_pair, "sensitivity_sol_only": _sensitivity_sol_only(plan_ps, [r for r in key.get("refused", []) if r.get("set") == "R" and r.get("phase") in PL.PLAN_BLOCKS])}


# ----------------------------------------------------------------------------- the report

def report(decs: dict, key: dict, population=None, investigations=None, k_commit=None, projection=None,
           replay_status=None, pair_plan=None) -> dict:
    ps = []
    for pid, p in decs["packets"].items():
        ps.append({"pid": pid, **p})
    plan_ps = [p for p in ps if p.get("in_plan")]        # the main block's plan: each packet scored by its own pair, in `main_by_pair`
    gps = [p for p in ps if not p.get("in_plan")]        # everything else (K, the pilot, any packet outside the plan): the report's `--pair`
    ks = [p for p in gps if p["set"] == "K"]
    cs = [p for p in gps if p["set"] == "C"]
    rs = [p for p in gps if p["set"] == "R"]
    ns = [p for p in gps if p["set"] == "N"]              # answered, never scored: no part below reads them
    gdecs = {p["pid"]: p for p in gps}
    pilot_c = [p for p in cs if p["phase"] in ("pilot", "calibration")]
    refused = key.get("refused", [])
    rk = [r for r in refused if r.get("set") == "K"]
    rc = [r for r in refused if r.get("set") == "C" and r.get("phase") in ("pilot", "calibration")]
    parts = {"1": _k_part1(ks, rk), "2": _k_part2(ks, rk), "3": _k_by_option(ks, rk),
             "4": _c_pilot(pilot_c, investigations, rc, population),
             "5": _part5(gdecs, key, population)}
    sts = [v["status"] for v in parts.values()]
    overall = "fail" if "fail" in sts else ("incomplete" if "incomplete" in sts else "pass")
    pending = {p["pid"]: p["pending"] for p in ps if p["pending"] and p["set"] != "N"}
    findings = []
    tc = parts["5"]["time_capped"]
    if tc["over_10_percent"]:
        findings.append({"finding": "time_capped_over_10_percent", "time_capped": {"k": tc["k"], "planned": tc["planned"], "share": tc["share"]},
                         "note": "K (runs ended by the time cap) exceeds 10% of the pilot's planned runs: its own finding, not an "
                                 "instrument failure, and it does not fail part 5"})
    if parts["4"]["cells_without_set_c"]:
        if parts["4"]["status"] == "not_tested":
            findings.append({"finding": "part_4_not_tested", "note": "no planned cell has a set C run: part 4 is not tested, never passed, and go rests on "
                             "the other parts, which the paper states (amendment 29(h)); section 8's replay is auxiliary"})
        findings.append({"finding": "cells_without_set_c", "cells": parts["4"]["cells_without_set_c"],
                         "n_cells_without_set_c": len(parts["4"]["cells_without_set_c"]),
                         "note": "no set C run in these planned option x layout cells of the pilot and the calibration: not tested on "
                                 "these cells (a gap, never a pass); part 4 is decided on the cells that have runs"})
    main_by_pair = None
    if plan_ps:
        if pair_plan is None:
            raise ValueError("the decisions hold packets of a coding plan: give the report its pair_plan")
        main_by_pair = _main_by_pair(plan_ps, key, pair_plan)
        if main_by_pair["not_coded"]["n"]:
            findings.append({"finding": "sonnet_subject_runs_not_coded", "n": main_by_pair["not_coded"]["n"],
                             "note": "the plan's Codex quota closed before the Sonnet subject runs, which go first, were all coded; they are never "
                                     "given Opus + Sonnet, so each stays unknown (not coded)"})
        if main_by_pair["sol"]["sonnet_subject_sol_quota_failed"]:
            findings.append({"finding": "sonnet_subject_runs_sol_quota_failed", "n": len(main_by_pair["sol"]["sonnet_subject_sol_quota_failed"]),
                             "note": "Sonnet subject runs whose Sol calls met the Codex limit and gave no valid answer: not reassigned, their Sol "
                                     "verdict is CANNOT TELL"})
    rep = {
        "format": FORMAT_REPORT,
        "header": {"coder_pair": list(CODERS), "coder_pairs": [list(CODERS), *[list(x) for x in PLAN_PAIRS if main_by_pair]],
                   "rubric": key.get("rubric"), "prompt_sha256": key.get("prompt_sha256"), "k_commit": k_commit,
                   "packets": dict(Counter(p["set"] for p in ps)),
                   "refused": {"n": len(key.get("refused", [])),
                               "reasons": [{"run_key": r.get("run_key"), "set": r.get("set"), "reason": r.get("reason")}
                                           for r in key.get("refused", [])]},
                   "pending": pending, "problems": decs.get("problems", []),
                   "instrument_label_missing": [p["pid"] for p in ps if p.get("instrument_missing")]},
        "parts": parts, "status": overall, "findings": findings,
        "set_n": _set_n(ns, [r for r in refused if r.get("set") == "N"]),
        "k_accuracy": _accuracy(ks), "k_stated_narrowing": _k_stated_narrowing(ks), "k_omitting_unstated": _k_omitting_unstated(ks), "kappa": _kappas(rs + cs, ks), "resolved_share": _resolved_share(rs, [r for r in refused if r.get("set") == "R"]),
        "coder_pair_on_c": _c_rates(cs, key.get("c_main_strata", [])),
        "c_sample": {"rule": key.get("c_rule"), "strata": key.get("c_main_strata", [])},        # the main block's set C: its rule, rates and realised sizes (counts only)
        "k_pair_error_rates": _k_rates(ks),
        "route_mix": _route_mix({p["pid"]: p for p in ps}, key, population), "tokens": _tokens(gdecs), "subagents": _subagents(gdecs),
        "tokens_by_option": _tokens_by(rs + cs, "option"), "tokens_by_model": _tokens_by(rs + cs, "model"),
        "limitations": LIMITATIONS,
        "independent_check": replay_status or dict(INDEPENDENT_CHECK)}
    if main_by_pair is not None:
        rep["main_by_pair"] = main_by_pair
    if projection:
        rep["projection"] = project(rep, projection)
    return rep


def gate_artifact(rep: dict) -> dict:
    h = rep["header"]
    return {"format": FORMAT_GATE, "rubric_sha256": (h.get("rubric") or {}).get("sha256"),
            "coder_pair": h.get("coder_pair"), "prompt_sha256": h.get("prompt_sha256"), "k_commit": h.get("k_commit"),
            "parts": rep["parts"], "status": rep["status"], "findings": rep["findings"], "kappa": rep["kappa"],
            "resolved_share": rep["resolved_share"], "k_pair_error_rates": rep["k_pair_error_rates"],
            "k_stated_narrowing": rep["k_stated_narrowing"], "k_omitting_unstated": rep["k_omitting_unstated"], "limitations": rep["limitations"], "independent_check": rep["independent_check"],
            "subagents": rep["subagents"],
            "tokens": {c: {s: v for s, v in by.items() if s == "all"} for c, by in rep["tokens"].items()}}


# ----------------------------------------------------------------------------- markdown

def _frac(d) -> str:
    return "n/a" if d is None else f"{d['k']}/{d['n']}"


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _md_main_by_pair(mp: dict) -> list[str]:
    L = ["", "## The main block, per coder pair (amendment 26)", mp["note"], "",
         f"- plan: seed {mp['plan']['seed']}, {mp['plan']['n_planned']} planned runs in {', '.join(mp['plan']['blocks'])}, sections {mp['plan']['sections']}, "
         f"plan sha256 {mp['plan']['plan_sha256']}",
         f"- packets of the plan: {mp['packets']}; runs per pair: {mp['runs_per_pair']}",
         f"- coded in the main block: {mp['coded_packets']}; coded and unused (in neither set R nor set C's sample): {mp['coded_unused']} "
         "(counted here, after the block, and nowhere before)"]
    s = mp["sol"]
    L.append(f"- how far Sol got: assigned to {s['assigned_sol']} run(s), the last at position {s['last_sol_position']} of {s['order_length']}; "
             f"first Opus + Sonnet run at position {s['first_fallback_position']}; reassigned after a Codex limit error: {s['reassigned_to_opus_sonnet']}")
    g = mp["gate"]
    if g is None:
        L.append("- quota gate: NO GATE FILE in the work directory (the runner has not run, or this is not its work directory)")
    else:
        L.append(f"- quota gate: **{g['mode'].upper()}** (wait {g['wait_s']:g} s for a reset, probes every {g['probe_s']:g} s, then every "
                 f"{g['probe_slow_s']:g} s after the switch); highest reading {g['max_used_percent']}%; {g['n_readings']} readings in "
                 f"{g['n_calls']} Codex calls and {g['n_probes']} probe(s); posts that failed: {g['n_post_failed']}")
        for ep in g["episodes"]:
            r = ep["reading"]
            re_ = ep["reopened_reading"] or {}
            L.append(f"  - closing {ep['episode']} at {ep['closed_at']} ({ep['reason']}): reading {r.get('used_percent')}% (window ends "
                     f"{r.get('resets_at_iso')}); posted {ep['posted_at']}; {ep['probes']} probe(s); switched to Opus + Sonnet "
                     f"{ep['switched_at']}; reopened {ep['reopened_at']} at {re_.get('used_percent')}%")
    nc = mp["not_coded"]
    if nc["n"]:
        L.append(f"- **ALARM: {nc['n']} Sonnet subject run(s) NOT CODED** ({nc['note']}); by reason {nc['by_reason']}; by cell {nc['by_cell']}")
    else:
        L.append("- Sonnet subject runs not coded: 0")
    if s["sonnet_subject_sol_quota_failed"]:
        L.append(f"- **ALARM: {len(s['sonnet_subject_sol_quota_failed'])} Sonnet subject run(s) met the Codex limit with no valid Sol answer** "
                 "(not reassigned: never Opus + Sonnet; their Sol verdict is CANNOT TELL)")
    L += ["", "### Runs per option x layout x model", "", "| cell | planned | sol+opus | opus+sonnet | not coded | not dispatched | no packet |", "|---|---|---|---|---|---|---|"]
    for c, v in mp["by_cell"].items():
        L.append(f"| {c} | {v['planned']} | {v['sol+opus']} | {v['opus+sonnet']} | {v['not_coded']} | {v['not_dispatched']} | {v['no_packet']} |")
    for name, b in mp["by_pair"].items():
        kp = b["kappa"]
        L += ["", f"### Pair {name} ({' + '.join(b['pair'])}): {b['packets']['R']} set R and {b['packets']['C']} set C packets "
                  f"({b['packets']['pending']} pending)", "", "| kappa group | n | kappa | observed | expected |", "|---|---|---|---|---|"]
        rows = [("real overall", kp["real_overall"])] + [(f"option {o}", v) for o, v in kp["real_by_option"].items()] + \
               [(f"model {m}", v) for m, v in kp["real_by_model"].items()]
        for nm, v in rows:
            kv = "null (" + v["why_null"] + ")" if v["kappa"] is None else f"{v['kappa']:.3f}"
            L.append(f"| {nm} | {v['n']} | {kv} | {_pct(v['observed'])} | {_pct(v['expected'])} |")
        rsh = b["resolved_share"]
        L.append(f"- share resolved (set R): {rsh['overall']['resolved']}/{rsh['overall']['n']} (pending {rsh['overall']['pending']})")
        for grp in ("by_option", "by_model"):
            for o, v in rsh[grp].items():
                L.append(f"  - {grp[3:]} {o}: {v['resolved']}/{v['n']}")
        for sect in ("main_raw", "main_by_model"):
            L.append(f"- set C, {sect} (Wilson 95%; {b['coder_pair_on_c']['note'][:60]}...)")
            for gk, v in b["coder_pair_on_c"][sect].items():
                fc, fo = v["false_complete"], v["false_omitting"]
                L.append(f"  - {gk}: false-complete {fc['k']}/{fc['n']} [{_pct(fc['lo'])}, {_pct(fc['hi'])}]; "
                         f"false-omitting {fo['k']}/{fo['n']} [{_pct(fo['lo'])}, {_pct(fo['hi'])}]")
        for c, by in b["tokens"].items():
            for st, v in by.items():
                if v["n"]:
                    L.append(f"- {name} {c} {st}: n={v['n']} tokens={v['tokens']} wall={v['wall_s']} cost={v['cost_usd']} attempts={v['attempts']}")
        for title, k in (("option", "tokens_by_option"), ("subject model", "tokens_by_model")):
            for gk, row in b[k].items():
                for c, v in row.items():
                    L.append(f"- {name} per {title} {gk} {c}: n={v['n']} tokens={v['tokens']} wall_s={v['wall_s']} cost={v['cost_usd']}")
    sn = mp["sensitivity_sol_only"]
    L += ["", "### Sensitivity row: Sol-coded runs only", sn["note"],
          f"- set R resolved by Sol + Opus: {sn['resolved_share']['resolved']}/{sn['resolved_share']['n']} "
          f"(of which Sol-coded R packets: {sn['resolved_share']['sol_coded_r_packets']}); labels after inspection {sn['labels_after_inspection']}"]
    for grp in ("by_option", "by_model"):
        for o, v in sn[grp].items():
            L.append(f"  - {grp[3:]} {o}: {v['resolved']}/{v['n']}")
    return L


def markdown(rep: dict) -> str:
    h, P = rep["header"], rep["parts"]
    L = ["# Blind inspection: gate report", "",
         f"Overall status: **{rep['status']}**", "",
         f"- rubric: {(h['rubric'] or {}).get('path')} sha256 {(h['rubric'] or {}).get('sha256')}",
         f"- prompt sha256: {h['prompt_sha256']}", f"- K set committed at: {h['k_commit']}",
         f"- packets: {h['packets']}", f"- refused packets: {h['refused']['n']}",
         f"- pending packets: {len(h['pending'])}", f"- problems: {len(h['problems'])}", ""]
    for r in h["refused"]["reasons"]:
        L.append(f"  - refused {r['run_key']} ({r['set']}): {r['reason']}")
    L += ["", "## Go criterion 3 (rubric 7)", "", "| part | status |", "|---|---|"]
    names = {"1": "K, pair against truth", "2": "K, full procedure", "3": "K by option",
             "4": "set C pilot", "5": "pilot unknown share"}
    for k in "12345":
        L.append(f"| {k} {names[k]} | {P[k]['status']} |")
    p1 = P["1"]
    L += ["", "### Part 1", f"- omitting cases answered COMPLETE by both: {_frac(p1['omitting_cases_answered_complete_by_both'])} (must be 0)",
          f"- complete cases answered COMPLETE by both: {_frac(p1['complete_cases_answered_complete_by_both'])} "
          f"= {_pct(p1['complete_cases_answered_complete_by_both']['share'])} (at least 80%)",
          f"- complete cases answered OMITTING by both: {_frac(p1['complete_cases_answered_omitting_by_both'])} (must be 0)",
          "", "### Part 2", f"- omitting cases ending complete: {_frac(P['2']['omitting_cases_ending_complete'])} (must be 0)",
          "", "### Part 3 (by option, option-matched subset)"]
    for o, v in P["3"]["options"].items():
        L.append(f"- {o}: {v['status']} (n={v['n']}); part 1 {v['part1']['status']}, part 2 {v['part2']['status']}")
    p4 = P["4"]
    L += ["", "### Part 4 (set C, pilot and calibration)",
          f"- COMPLETE by both while instrument omitting: {_frac(p4['answered_complete_by_both_while_instrument_omitting'])} (must be 0)",
          f"- OMITTING by both while instrument complete: {_frac(p4['answered_omitting_by_both_while_instrument_complete'])} (at most 10%)",
          f"- the pilot's own figures, beside (not decided on alone): {p4['pilot_only']['n_runs']} runs; COMPLETE by both while instrument omitting "
          f"{p4['pilot_only']['answered_complete_by_both_while_instrument_omitting']['k']} of {p4['pilot_only']['answered_complete_by_both_while_instrument_omitting']['n']}; "
          f"OMITTING by both while instrument complete {p4['pilot_only']['answered_omitting_by_both_while_instrument_complete']['k']} of {p4['pilot_only']['answered_omitting_by_both_while_instrument_complete']['n']}",
          f"- disagreements: {len(p4['disagreements'])}; pending investigation: {len(p4['pending_investigation'])}"]
    for d in p4["disagreements"]:
        L.append(f"  - {d['pid']} {d['run_key']} instrument {d['instrument']} coders {d['coders']} ({d['kind']}): {d['note'] or 'PENDING INVESTIGATION'}")
    cells = p4["set_c_cells"]
    if not cells["checked"]:
        L.append(f"- set C runs per option x layout cell: NOT CHECKED ({cells['note']})")
    else:
        L.append("- set C runs per planned option x layout cell (pilot / calibration, apart): "
                 + "; ".join(f"{c} {v['set_c_pilot']} / {v['set_c_calibration']}" for c, v in cells["cells"].items()))
        if cells["cells_without_set_c"]:
            L.append(f"- **NOT TESTED on {cells['n_cells_without_set_c']} of {cells['n_cells']} cell(s), which have no set C run: "
                     f"{', '.join(cells['cells_without_set_c'])}.** A gap in the gate, never a pass; part 4 is decided on the cells that have runs.")
    p5 = P["5"]
    tc = p5["time_capped"]
    L += ["", "### Part 5 (pilot runs left unknown, over the planned runs that are not time-capped)",
          f"- unknown after inspection, plus runs left without a label for any reason other than the time cap: {_frac(p5['unknown'])} = "
          f"{_pct(p5['unknown']['share'])} (at most 10%); basis: {p5['basis']}",
          f"- planned runs: {p5['planned_runs']}; K (runs ended by the time cap; out of the share, and not set K): {tc['k']} of {tc['planned']} = {_pct(tc['share'])}",
          f"- of the runs counted, unlabelled for another reason (not finished, lost, never started; counted unknown): {len(p5['unlabelled_unknown'])}",
          f"- calibration (information only): {_frac(p5['calibration_information_only']['unknown'])}"]
    for f in rep["findings"]:
        L.append(f"- **FINDING {f['finding']}:** {f['note']}")
    sn = rep["set_n"]
    L += ["", "## Set N (pilot runs with no label): answered, NOT scored against any label",
          f"- {sn['packets']} packet(s) ({sn['time_capped_packets']} time-capped), {sn['refused']} refused; {sn['note']}"]
    for c, v in sn["by_coder"].items():
        L.append(f"- {c}: answered {v['answered']}, pending {v['pending']} (COMPLETE {v['COMPLETE']}, OMITTING {v['OMITTING']}, "
                 f"CANNOT_TELL {v['CANNOT_TELL']}, MALFORMED {v['MALFORMED']})")
    un = rep["k_omitting_unstated"]
    L += ["", f"## K's omitting cases that don't state their narrowing, pair {' + '.join(un['pair'])}", "Only the code can give these away, so these are the K numbers to read first.",
          f"- **OMITTING by both: {un['both_omitting']} of {un['n']}**; COMPLETE by both: {un['both_complete']} (95% upper bound {_pct(un['both_complete_upper95'])}); "
          f"not OMITTING by both: {un['not_both_omitting']} (95% upper bound {_pct(un['not_both_omitting_upper95'])}); pending {un['pending']}"]
    for o, b in un["by_option"].items():
        L.append(f"  - option {o}: OMITTING by both {b['both_omitting']} of {b['n']}; COMPLETE by both {b['both_complete']}")
    L += ["", "## Each coder on K"]
    for c, a in rep["k_accuracy"].items():
        L.append(f"- {c}: correct {_frac(a['correct'])}, wrong {a['wrong']}, cannot tell {a['cannot_tell']}, "
                 f"malformed {a['malformed']}, pending {a['pending']}")
        for o, b in a.get("by_option", {}).items():
            L.append(f"  - option {o}: correct {b['correct']} of {b['n']}, wrong {b['wrong']} "
                     f"(95% upper bound {_pct(b['wrong_upper95'])}), not correct {b['not_correct']} "
                     f"(95% upper bound {_pct(b['not_correct_upper95'])}), pending {b['pending']}")
        if a.get("superset_extractions"):
            L.append(f"  - {a['superset_extractions']} omitting case(s) where {c} names more parts than the case's note; its verdict is right, section 7 scores no parts, "
                     "and K is left as it is, as truth is never taken from a coder. The coders' coverage comes only from extractions that agree exactly.")
            for x in a["superset_answers"]:
                L.append(f"    - {x['pid']}: the note says {', '.join(x['truth_parts'])}; {c} names {', '.join(x['named_parts'])}")
    L.append("- The upper bounds are exact (Clopper-Pearson, two-sided 95%): a perfect score on few cases bounds little, "
             "so set C (real, instrument-decided runs) weighs more where an option has few K cases (science, #76, 20:12Z).")
    sn = rep["k_stated_narrowing"]
    L += ["", "## K with and without omitting cases that state the narrowing (descriptive, not part of the gate)",
          f"Omitting cases that openly say less data is used: {sn['tagged']} of {sn['omitting']} = {_pct(sn['share_of_omitting'])}; "
          + ", ".join(f"{g}: {v['tagged']} of {v['omitting']}" for g, v in sn["by_group"].items()) + "."]
    for c in rep["k_accuracy"]:
        L.append(f"- {c}: all cases correct {_frac(sn['all_cases']['with'][c]['correct'])}, without them {_frac(sn['all_cases']['without'][c]['correct'])}; "
                 f"omitting cases correct {_frac(sn['omitting_cases']['with'][c]['correct'])}, without them {_frac(sn['omitting_cases']['without'][c]['correct'])}")
    L += ["", "## Cohen's kappa between the coders", rep["kappa"]["note"], "", "| group | n | kappa | observed | expected |", "|---|---|---|---|---|"]
    kp = rep["kappa"]
    rows = [("real overall", kp["real_overall"]), ("K", kp["k_overall"])]
    rows += [(f"option {o}", v) for o, v in kp["real_by_option"].items()]
    rows += [(f"model {m}", v) for m, v in kp["real_by_model"].items()]
    for name, v in rows:
        kv = "null (" + v["why_null"] + ")" if v["kappa"] is None else f"{v['kappa']:.3f}"
        L.append(f"| {name} | {v['n']} | {kv} | {_pct(v['observed'])} | {_pct(v['expected'])} |")
    L += ["", "## Coder pair against truth on K (Wilson 95%)"]
    kr = rep["k_pair_error_rates"]
    for g, v in [("overall", kr["overall"])] + [(f"option {o}", v) for o, v in kr["by_option"].items()]:
        fc, fo = v["false_complete"], v["false_omitting"]
        L.append(f"- {g}: false-complete {fc['k']}/{fc['n']} [{_pct(fc['lo'])}, {_pct(fc['hi'])}]; "
                 f"false-omitting {fo['k']}/{fo['n']} [{_pct(fo['lo'])}, {_pct(fo['hi'])}]")
    L += ["", "## Share resolved (set R)"]
    rsh = rep["resolved_share"]
    L.append(f"- overall: {rsh['overall']['resolved']}/{rsh['overall']['n']} (pending {rsh['overall']['pending']}, "
             f"refused {rsh['overall']['refused']}, counted unresolved)")
    for g in ("by_option", "by_model"):
        for o, v in rsh[g].items():
            L.append(f"- {g[3:]} {o}: {v['resolved']}/{v['n']}")
    L += ["", "## Coder pair on set C (Wilson 95%)"]
    cp = rep["coder_pair_on_c"]
    for sect in ("pilot_and_calibration_raw", "main_raw"):
        L.append(f"- {sect}")
        for g, v in cp[sect].items():
            fc, fo = v["false_complete"], v["false_omitting"]
            L.append(f"  - {g}: false-complete {fc['k']}/{fc['n']} [{_pct(fc['lo'])}, {_pct(fc['hi'])}]; "
                     f"false-omitting {fo['k']}/{fo['n']} [{_pct(fo['lo'])}, {_pct(fo['hi'])}]")
    for sect in ("pilot_and_calibration_by_model", "main_by_model"):
        L.append(f"- {sect}")
        for g, v in cp[sect].items():
            fc, fo = v["false_complete"], v["false_omitting"]
            L.append(f"  - {g}: false-complete {fc['k']}/{fc['n']} [{_pct(fc['lo'])}, {_pct(fc['hi'])}]; "
                     f"false-omitting {fo['k']}/{fo['n']} [{_pct(fo['lo'])}, {_pct(fo['hi'])}]")
    L.append("- main_reweighted: " + json.dumps(cp["main_reweighted"]["total"]))
    L += ["", "## Route mix", json.dumps(rep["route_mix"].get("overall") or rep["route_mix"]), "", "## Subagents"]
    sa = rep["subagents"]
    if sa["to_science_before_the_pilot"]:
        L.append(f"**To science before the pilot's packets:** {', '.join(sa['to_science_before_the_pilot'])} above {sa['k_rate_to_science']:.0%} on K.")
    for c, by in sa["by_coder"].items():
        for s, v in by.items():
            if v["packets"] or v["not_recorded"]:
                L.append(f"- {c} {s}: {v['with_subagent']}/{v['packets']} packets with a subagent ({_pct(v['rate'])}); not recorded {v['not_recorded']}")
    L += ["", "## Tokens, wall time, cost"]
    for c, by in rep["tokens"].items():
        for s, v in by.items():
            if v["n"]:
                L.append(f"- {c} {s}: n={v['n']} tokens={v['tokens']} wall={v['wall_s']} cost={v['cost_usd']} "
                         f"attempts={v['attempts']} retried={v['retried_attempts']} contaminated={v['contaminated_attempts']}")
    for title, k in (("option", "tokens_by_option"), ("subject model", "tokens_by_model")):
        L += ["", f"### Tokens and cost per {title} (real runs)"]
        for g, row in rep[k].items():
            for c, v in row.items():
                L.append(f"- {g} {c}: n={v['n']} tokens={v['tokens']} wall_s={v['wall_s']} cost={v['cost_usd']}")
    if "main_by_pair" in rep:
        L += _md_main_by_pair(rep["main_by_pair"])
    L += ["", "## Independent check", f"- {rep['independent_check']['status']}: {rep['independent_check']['note']}",
          "", "## Stated limitations"] + [f"- {x}" for x in rep["limitations"]]
    if "projection" in rep:
        L += ["", "## Projection", rep["projection"]["note"], "", json.dumps(rep["projection"]["total"])]
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- CLI

def _parse_projection(s):
    if not s:
        return None
    out = {}
    for part in s.split(","):
        k, v = part.split("=")
        out[k.strip()] = int(v)
    return out


def set_pair(pair) -> tuple[str, str]:
    """Which two coders this report scores. A gate is reported per pair, never pooled across pairs."""
    global CODERS
    pair = tuple(pair)
    if len(pair) != 2 or len(set(pair)) != 2 or not set(pair) <= set(KNOWN_CODERS):
        raise ValueError(f"a pair is two different coders of {KNOWN_CODERS}, not {pair}")
    CODERS = pair
    return CODERS


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pair", default="codex,claude", help="the two coders to score the K and pilot parts, as coder,coder: codex,claude or sonnet,claude")
    ap.add_argument("--pair-plan", help="the main block's coding plan (plan.py): each packet of it is scored by its own pair, from <sealed>/answers/<packet>/pair.json")
    ap.add_argument("--key", help="the gate's key (set K, the pilot); with --sealed it is joined with the main block's key built here")
    ap.add_argument("--work", required=True, help="the work directory (the gate's answers and, with --sealed, the public gate files in <work>/quota)")
    ap.add_argument("--sealed", help="the main block's sealed directory (plan.py): needs --pair-plan, --population and --unseal")
    ap.add_argument("--unseal", action="store_true",
                    help="read the sealed directory. Under amendment 29(c) the SCIENCE agent alone runs snapshots and reads their tables; no lane that runs "
                         "the campaign computes a contrast. That rests on instruction, not on a lock (mode 700 guards against accidents only)")
    ap.add_argument("--c-main-per-cell", type=int, default=15)
    ap.add_argument("--population")
    ap.add_argument("--investigations")
    ap.add_argument("--k-commit")
    ap.add_argument("--project")
    ap.add_argument("--packets", help="directory with <pid>.lines.json")
    ap.add_argument("--replay-status", help="JSON file {status, note} overriding the independent-check entry")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    set_pair(a.pair.split(","))
    try:
        PL.require_unsealed(a.work, a.unseal)
        if a.sealed:
            if not (a.pair_plan and a.population):
                ap.error("--sealed needs --pair-plan and --population")
            if a.key and not a.packets:
                ap.error("--key with --sealed needs --packets too: the gate's packets are read from there")
        elif not (a.key and a.packets):
            ap.error("--key and --packets are required (without --sealed)")
    except PL.SealError as e:
        print(f"icsa.inspection.report: {e}", file=sys.stderr)
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for n in OUTPUTS:                      # never leave a stale output next to a failed run
        (out / n).unlink(missing_ok=True)
    from icsa.instances.load import load_required_extents
    from .queue import read_population
    try:
        if a.sealed:
            key, pair_plan, pop = PL.main_inputs(a.pair_plan, a.sealed, a.population, a.work, key_path=a.key, unseal=a.unseal,
                                                 c_main_per_cell=a.c_main_per_cell)
        else:
            key = json.loads(Path(a.key).read_text())
            pair_plan = PL.PairPlan.load(a.pair_plan, a.work, key) if a.pair_plan else None
            pop = read_population(a.population) if a.population else None
    except (PL.SealError, PL.PlanError) as e:
        print(f"icsa.inspection.report: {e}", file=sys.stderr)
        return 2
    extents = load_required_extents()
    decs = decisions(key, a.work, lambda iid: extents[iid], a.packets or ".", pair_plan, unseal=a.unseal)
    inv = json.loads(Path(a.investigations).read_text()) if a.investigations else None
    replay = json.loads(Path(a.replay_status).read_text()) if a.replay_status else None
    rep = report(decs, key, pop, inv, a.k_commit, _parse_projection(a.project), replay, pair_plan)
    (out / "decisions.json").write_text(json.dumps(decs, indent=1, sort_keys=True, default=str))
    (out / "report.json").write_text(json.dumps(rep, indent=1, sort_keys=True, default=str))
    (out / "report.md").write_text(markdown(rep))
    (out / "inspection_gate.json").write_text(json.dumps(gate_artifact(rep), indent=1, sort_keys=True, default=str))
    print(f"inspection gate: {rep['status']} ({', '.join(f'{k}:{v['status']}' for k, v in rep['parts'].items())})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
