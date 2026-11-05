"""The six go criteria, each a separate computed check (protocol/parameters.md, "Pilot go criteria").

Each function takes explicit artifacts, never scans a directory, and returns a CheckResult.
"""
from __future__ import annotations

import json
import pathlib

from icsa.records import Layout, Option, OmissionLabel

from .core import FAIL, MISSING, PASS, Artifact, CheckResult, Evidence, missing

SRC = "protocol/parameters.md, row 'Pilot go criteria'"
UNKNOWN_MAX = 0.10          # issue #18 criterion 3: share of unknown labels <= 10%
FAULT_MIN_FAULTED, FAULT_MIN_CONTROL = 60, 30      # parameters.md, row 'H3 test'
SCRIPTED_OPTIONS = tuple(o.value for o in Option)  # T, T-unpaginated, D, M, M+ (#9's five options)
PILOT_OPTIONS = ("T", "D", "M")                    # the pilot block's options (#16 config)
LAYOUTS = tuple(l.value for l in Layout)
FAULT_OPTIONS = ("T", "D", "M")                    # icsa.faults.observability.OPTIONS
CELLS6 = [(o, l) for o in ("T", "D", "M") for l in LAYOUTS]
REQUIRED_BLOCKS = ("south", "oslo", "bothnian", "archip", "nanpaths", "y1982")   # reports/refdet/SCOPE.md: six Octave blocks


def _res(n, title, src, reasons, ev, details=None, absent=()):
    """`reasons` are measured failures; `absent` are inputs that are not there. A failure wins over absence."""
    status = FAIL if reasons else (MISSING if absent else PASS)
    return CheckResult(n, title, status, list(reasons) + [f"MISSING: {a}" for a in absent], src, ev, details or [])


# ------------------------------------------------------------------ 1
def c1_reference(eq: Artifact, validation: Artifact | None = None, gt_record: Artifact | None = None,
                 required_blocks=REQUIRED_BLOCKS) -> CheckResult:
    title = "Reference passes the equivalence validation (#4)"
    src = SRC + " (i); parameters.md 'Equivalence criterion' c1-c4"
    if not eq.usable or not isinstance(eq.data, list):
        return missing(1, title, src, eq)
    reasons, details, absent = [], [], []
    names = [b.get("block") for b in eq.data]
    if len(set(names)) != len(names):
        reasons.append(f"duplicate block rows: {sorted(n for n in set(names) if names.count(n) > 1)}")
    lacking = [n for n in required_blocks if n not in names]
    if lacking:
        absent.append(f"validation blocks absent: {lacking} (required: reports/refdet/SCOPE.md)")
    for b in eq.data:
        bad = [k for k in ("c1", "c2", "c3", "c4") if b.get(f"{k}_pass") is False]
        absent += [f"block {b.get('block')}: no {k}_pass flag" for k in ("c1", "c2", "c3", "c4") if f"{k}_pass" not in b or b[f"{k}_pass"] is None]
        details.append(f"block {b.get('block')}: " + ", ".join(f"{k}={b.get(f'{k}_pass')}" for k in ("c1", "c2", "c3", "c4")))
        if bad:
            reasons.append(f"block {b.get('block')}: {', '.join(bad)} not passed")
    ev = [eq.evidence("equivalence blocks")]
    details.append("Ground truth mode: computed, on the S1/S2 values the agents read (parameters.md, reference rule).")
    if gt_record is not None:
        if not gt_record.usable or not isinstance(gt_record.data, dict) or not gt_record.data.get("complete") \
                or not gt_record.data.get("source_fingerprint"):
            absent.append("ground-truth field cache record is missing, a stub, incomplete or has no fingerprint")
        else:
            details.append(f"Ground-truth field cache: source fingerprint {gt_record.data['source_fingerprint']}, "
                           f"created {gt_record.data.get('created_utc')}.")
        ev.append(gt_record.evidence("field cache record"))
    if validation is not None and validation.usable:
        d = validation.data
        ea = d.get("events", {})
        details.append("Agreement with the published catalogue (reported, not gated; nothing is tuned to recover the 189):")
        for k in sorted(k for k in ea if isinstance(ea[k], dict)):
            e = ea[k]
            details.append(f"  variant {k}: published {e.get('published')}, ours {e.get('ours')}, "
                           f"exact matches {e.get('exact_matches')}, published events overlapped {e.get('published_overlapped')}")
        maps = d.get("maps", [])
        details.append(f"  daily event maps compared: {len(maps)}")
        ev.append(validation.evidence("189-event comparison"))
    else:
        details.append("189-event comparison: input missing (reported only, not gated).")
    return _res(1, title, src, reasons, ev, details, absent)


# ------------------------------------------------------------------ 2
FAIL_LISTS = ("failed", "omitting_called_complete", "complete_not_called_complete", "analysed_not_exact_resolved",
              "loaded_not_exact", "bound_unsound", "read_not_superset", "read_not_observed", "listing_mismatch")


# The re-validated #9 summary names itself: the method baseline window, compressed (deflate) data, and the
# science ruling on #9 (1 Nov 14:02Z): the full matrix on the local path plus a real-path confirmation set on site_g.
REVALIDATED = {"baseline_window": "method", "data_kind": "compressed", "gates": "local-sim+real-confirmed"}


def revalidation_problems(s: dict) -> list[str]:
    """Why a #9 summary is not the re-validated one (empty list: it is).

    The gates label alone is not trusted: the summary must also carry the confirmation set's result, with runs
    and an empty list of label or analysed-extent differences against the local path. Per the #9 ruling, any
    difference keeps the criterion MISSING until it is explained and fixed, so it is a reason here, not a FAIL."""
    out = [f"summary field '{k}' is {s.get(k)!r}, the re-validated #9 run needs {v!r}"
           for k, v in REVALIDATED.items() if s.get(k) != v]
    rc = s.get("real_confirmation")
    if not isinstance(rc, dict):
        out.append("summary has no 'real_confirmation' result (the real-path confirmation set on site_g)")
        return out
    runs, diffs = rc.get("runs"), rc.get("differences")
    if not isinstance(runs, int) or isinstance(runs, bool) or runs <= 0:
        out.append(f"real_confirmation.runs is {runs!r}: the confirmation set has no runs")
    if not isinstance(diffs, list):
        out.append("real_confirmation has no 'differences' list")
    elif diffs:
        out.append(f"real_confirmation found {len(diffs)} difference(s) from the local path; "
                   "criterion 2 stays MISSING until they are explained and fixed")
    # Science ruling (#9, 1 Nov 16:56Z): while `read`, `read_beyond_days` or `listing` (T, T-unpaginated, D) is None on real
    # runs, criterion 2 is MISSING: an all-None record looks like success. The confirmation must say so itself.
    nf = rc.get("none_fields")
    if not isinstance(nf, list):
        out.append("real_confirmation has no 'none_fields' list (the fields left None on the real runs)")
    elif nf:
        out.append(f"real_confirmation: {len(nf)} field(s) are None on the real runs ({', '.join(map(str, nf[:6]))}"
                   f"{', ...' if len(nf) > 6 else ''}); criterion 2 stays MISSING until they are populated")
    return out


# The pilot's own None counts per option (written by the pipeline lane; STUB FORMAT until it exists, a stub gives MISSING):
#   {"none_counts": {"T": {"runs": n, "read": k, "read_beyond_days": k, "listing": k}, "T-unpaginated": {...}, "D": {...},
#                    "M": {"runs": n, "read": k, "read_beyond_days": k}}}
# k = runs of that option whose field is None; every counted field must be 0. Science ruling (#9, 16:56Z): `read` and
# `read_beyond_days` on a real run in EVERY pilot option (M included); `listing` for T, T-unpaginated and D only (M lists with
# os.listdir, whose extent the tracer records differently, so M's `listing` is neither required nor checked). M+ is not in the pilot.
NONE_FIELDS_BY_OPTION = {"T": ("read", "read_beyond_days", "listing"), "T-unpaginated": ("read", "read_beyond_days", "listing"),
                         "D": ("read", "read_beyond_days", "listing"), "M": ("read", "read_beyond_days")}
NONE_FIELD_OPTIONS = tuple(NONE_FIELDS_BY_OPTION)


def none_count_problems(art: Artifact | None) -> list[str]:
    if art is None or art.path is None:
        return ["no per-option None counts of the pilot (input 'none_counts' not configured): cannot tell all-None from success"]
    if not art.usable:
        return [f"per-option None counts of the pilot are unusable: {art.why_unusable()}"]
    nc = art.data.get("none_counts") if isinstance(art.data, dict) else None
    if not isinstance(nc, dict):
        return ["per-option None counts have no 'none_counts' object"]
    out = []
    for o, fields in NONE_FIELDS_BY_OPTION.items():
        row = nc.get(o)
        if not isinstance(row, dict):
            out.append(f"none_counts has no entry for option {o}")
            continue
        runs = row.get("runs")
        if not isinstance(runs, int) or isinstance(runs, bool) or runs <= 0:
            out.append(f"none_counts[{o}].runs is {runs!r}: no real runs counted")
        for f in fields:
            k = row.get(f)
            if not isinstance(k, int) or isinstance(k, bool) or k < 0:
                out.append(f"none_counts[{o}].{f} is {k!r}, not a count")
            elif k > 0:
                out.append(f"none_counts[{o}].{f} is None on {k} of {runs} run(s)")
    return out


def c2_instruments(summary: Artifact, readme_note: str | None = None, none_counts: Artifact | None = None) -> CheckResult:
    title = "Instruments reproduce the scripted runs for every option (#9)"
    src = SRC + " (ii)"
    if not summary.usable or not isinstance(summary.data, dict):
        return missing(2, title, src, summary)
    s = summary.data
    reasons, absent = [], []
    for k in FAIL_LISTS:
        if not isinstance(s.get(k), list):
            absent.append(f"summary has no '{k}' list")
        elif s[k]:
            reasons.append(f"{k}: {len(s[k])} entries")
    bo = s.get("by_option", {})
    for o in SCRIPTED_OPTIONS:
        if not bo.get(o) or not bo[o].get("runs"):
            absent.append(f"option {o}: no scripted runs in the summary")
    if not s.get("runs"):
        absent.append("no scripted runs")
    absent += [f"not the re-validated #9 summary: {x}" for x in revalidation_problems(s)]
    absent += [f"None fields: {x}" for x in none_count_problems(none_counts)]
    details = [f"scripted runs: {s.get('runs')}; per option: " +
               ", ".join(f"{o}={bo.get(o, {}).get('runs')}" for o in SCRIPTED_OPTIONS)]
    if readme_note:
        details.append(readme_note)
    return _res(2, title, src, reasons, [summary.evidence("instrument validation summary")], details, absent)


# ------------------------------------------------------------------ 3
RUN_KEY = "{instance_id}|{option}|{layout}|{model}|{seed}"
INSPECTION_FORMAT = "icsa-pilot-inspections-v1"
PILOT_RUNS = 30


def run_key(run: dict) -> str:
    return RUN_KEY.format(**{k: run[k] for k in ("instance_id", "option", "layout", "model", "seed")})


def c3_labels(summary: Artifact, scored: Artifact, planted: Artifact | None = None, inspections: Artifact | None = None,
              pilot_block: str = "pilot", unknown_max: float = UNKNOWN_MAX, pilot_runs: int = PILOT_RUNS) -> CheckResult:
    """The truth is never the instrument's own view. Scripted runs: the omission known by construction (#9's
    by_true_label, #11's planted `true` labels). Pilot agent runs: every run inspected by code reading (#35)."""
    title = "No omitting run labelled complete (truth independent of the instrument); unknown share <= 10% (#9, #11, pilot)"
    src = SRC + " (iii); share bound from issue #18"
    reasons, details, absent = [], [], []
    planted = planted if planted is not None else Artifact(None)
    inspections = inspections if inspections is not None else Artifact(None)
    # --- scripted runs: truth by construction
    if not summary.usable or not isinstance(summary.data, dict):
        absent.append("scripted summary: " + summary.why_unusable())
    else:
        s = summary.data
        absent += [f"scripted truth, not the re-validated #9 summary: {x}" for x in revalidation_problems(s)]
        ocs = s.get("omitting_called_complete")
        btl = s.get("by_true_label")
        om = btl.get("omitting") if isinstance(btl, dict) else None
        if ocs is None:
            absent.append("scripted summary has no omitting_called_complete field")
        elif ocs:
            reasons.append(f"scripted: {len(ocs)} runs omitting by construction were labelled complete")
        if om is None:
            absent.append("scripted summary has no by_true_label.omitting field")
        else:
            if not isinstance(om, dict) or any(not isinstance(v, int) for v in om.values()):
                absent.append("scripted summary: by_true_label.omitting is not a mapping of counts")
                om = {k: v for k, v in om.items() if isinstance(v, int)} if isinstance(om, dict) else {}
            if om.get("complete", 0):
                reasons.append(f"scripted: by_true_label counts {om['complete']} omitting-by-construction runs labelled complete")
            if sum(om.values()) == 0:
                absent.append("scripted summary has no run omitting by construction")
        details.append(f"scripted (truth by construction): omitting runs {None if om is None else sum(om.values())}, "
                       f"labelled complete {None if ocs is None else len(ocs)} (list) / {None if om is None else om.get('complete', 0)} (counts)")
        share = s.get("unknown_share_core")
        if share is None:
            absent.append("scripted summary has no unknown_share_core field")
        elif share > unknown_max:
            reasons.append(f"scripted: unknown share {share:.3f} > {unknown_max}")
        details.append(f"scripted unknown share over the core scenarios = {share} (the stress_print scenario is excluded, #9)")
    if not planted.usable or not isinstance(planted.data, dict):
        absent.append("planted faults (#11): " + planted.why_unusable())
    else:
        pr = planted.data.get("runs")
        if not isinstance(pr, list) or not all(isinstance(r, dict) for r in pr):
            absent.append("planted faults: no `runs` list of rows")
            pr = [r for r in pr if isinstance(r, dict)] if isinstance(pr, list) else []
        labels = {l.value for l in OmissionLabel}
        bad_rows = [r for r in pr if r.get("true") not in ("omitting", "complete") or r.get("label") not in labels]
        if bad_rows:
            absent.append(f"planted faults: {len(bad_rows)} rows lack a valid `true` or a `label`")
        om = [r for r in pr if r.get("true") == "omitting"]
        if not om:
            absent.append("planted faults: no run omitting by construction")
        wrong = [r for r in om if r.get("label") == "complete"]
        if wrong:
            reasons.append(f"planted faults: {len(wrong)} of {len(om)} planted omissions labelled complete")
        details.append(f"planted faults (truth = the planted `true` label): omitting {len(om)}, labelled complete {len(wrong)}")
    # --- pilot agent runs
    if not scored.usable:
        absent.append("pilot scored rows: " + scored.why_unusable())
        rows = []
    else:
        rows = [r for r in scored.data if r.get("block") == pilot_block]
        tot_lab = tot_unk = 0
        for o in PILOT_OPTIONS:
            ro = [r for r in rows if r["run"]["option"] == o]
            lab = [r for r in ro if r.get("label") is not None]
            if not lab:
                absent.append(f"pilot option {o}: no labelled agent run")
                details.append(f"pilot {o}: runs {len(ro)}, labelled 0")
                continue
            unk = sum(r["label"] == OmissionLabel.UNKNOWN.value for r in lab)
            tot_lab += len(lab); tot_unk += unk
            if unk / len(lab) > unknown_max:
                reasons.append(f"pilot option {o}: unknown share {unk}/{len(lab)} > {unknown_max}")
            details.append(f"pilot {o}: runs {len(ro)}, labelled {len(lab)}, unknown {unk} ({unk/len(lab):.3f})")
        if tot_lab:
            details.append(f"pilot pooled: unknown {tot_unk}/{tot_lab} ({tot_unk/tot_lab:.3f}); denominator = runs with a label")
        unlabelled = sum(r.get("label") is None for r in rows)
        if unlabelled:
            absent.append(f"pilot: {unlabelled} of {len(rows)} agent runs carry no label")
        keys = [run_key(r["run"]) for r in rows]
        if len(set(keys)) != len(keys):
            absent.append(f"pilot: {len(keys) - len(set(keys))} duplicate run keys among the {len(keys)} scored rows")
        if len(set(keys)) < pilot_runs:
            absent.append(f"pilot: {len(set(keys))} distinct agent runs, {pilot_runs} expected")
    if not inspections.usable or not isinstance(inspections.data, dict):
        absent.append("pilot inspections (#35 audit output): " + inspections.why_unusable())
    elif rows:
        ins = inspections.data.get("inspections")
        if not isinstance(ins, dict):
            absent.append("pilot inspections: no `inspections` mapping")
            ins = {}
        if inspections.data.get("format") != INSPECTION_FORMAT:
            absent.append(f"pilot inspections: format is not {INSPECTION_FORMAT}")
        n_done = n_wrong = 0
        lacking = []
        seen = set()
        for r in rows:
            k = run_key(r["run"])
            v = ins.get(k)
            truth = v.get("truth") if isinstance(v, dict) else v
            first = k not in seen
            seen.add(k)
            if truth not in ("omitting", "complete"):
                if first:
                    lacking.append(k)       # no entry, null (pending) or undecidable: not inspected to a verdict
                continue
            n_done += first
            if truth == "omitting" and r.get("label") == OmissionLabel.COMPLETE.value:
                n_wrong += 1
                reasons.append(f"pilot run {k}: inspected as omitting, labelled complete")
        if lacking:
            absent.append(f"pilot inspections: {len(lacking)} of {len(seen)} runs have no decisive code-reading verdict "
                          f"(first: {lacking[0]})")
        details.append(f"pilot code-reading inspections (truth): {n_done} of {len(seen)} runs judged, "
                       f"omitting-labelled-complete {n_wrong}")
    # --- diagnostic row, not the criterion
    if scored.usable:
        for o in PILOT_OPTIONS:
            comp = [r for r in rows if r["run"]["option"] == o and r.get("label") == OmissionLabel.COMPLETE.value]
            short = sum(r.get("complete_extent") is False for r in comp)
            none = sum(r.get("complete_extent") is None for r in comp)
            details.append(f"Diagnostic, not the criterion (label vs complete_extent, #13's scorer, the instrument's own view): "
                           f"option {o}: complete-labelled {len(comp)}, complete_extent false {short}, not recorded {none}")
    return _res(3, title, src, reasons, [summary.evidence("scripted"), planted.evidence("planted faults"),
                                         scored.evidence("pilot scored rows"), inspections.evidence("pilot inspections")],
                details, absent)


# ------------------------------------------------------------------ 4
def _live_problem(v: dict) -> str | None:
    """The rules of icsa.faults.observability._load_live: a valid class, a time-zoned non-future time, evidence."""
    import datetime as dt
    if not isinstance(v, dict):
        return "entry is not an object"
    for f in ("class", "recorded_at", "evidence"):
        if v.get(f) is None:
            return f"MISSING: field `{f}` absent or null"
    if v.get("class") not in ("observable", "unobservable_by_design"):
        return "class must be observable or unobservable_by_design"
    try:
        when = dt.datetime.fromisoformat(v["recorded_at"])
    except (KeyError, TypeError, ValueError):
        return "recorded_at missing or not an ISO time"
    if when.tzinfo is None:
        return "recorded_at has no time zone"
    if when > dt.datetime.now(dt.timezone.utc):
        return "recorded_at is in the future"
    if not isinstance(v.get("evidence"), str) or not v["evidence"].strip():
        return "no evidence"
    return None


_ALLOCATION = tuple(f"n_{s}_{k}" for s in ("invalid", "lost", "pending", "withheld") for k in ("faulted", "control"))


def _complete_cell(r: dict) -> bool | None:
    """Does H3's row show its whole planned allocation scored? (science, #2, 2 Nov: "every planned run is run once".)
    True; False when a measured count disproves it (a planned run with no result, a plan below the registered size, or H3's
    own status "incomplete"); None when something it needs is not recorded."""
    gone = [r.get(c) for c in _ALLOCATION]
    pf, pc = r.get("n_planned_faulted"), r.get("n_planned_control")
    if any(c is not None and c > 0 for c in gone) or (pf is not None and pf < FAULT_MIN_FAULTED) \
            or (pc is not None and pc < FAULT_MIN_CONTROL) or r.get("status") == "incomplete":
        return False
    return None if pf is None or pc is None or r.get("status") is None or any(c is None for c in gone) else True


def c4_records_and_faults(live: Artifact, fault_cells: Artifact, calibration_started: str | list | None = None) -> CheckResult:
    """Live classes filed and timestamped before the first calibration run; fault injection has run for every
    option x record with at least one complete cell: H3's tested row (`fidelity.h3_table`) shows every planned run of the cell
    scored, from a plan of the registered size. H3's own status and meets_h3 are reported, never gated."""
    title = "Read records calibrated before the runs; fault injection has run for every option x record (#10, #11)"
    src = SRC + " (iv); cell size from parameters.md 'H3 test'"
    import datetime as dt
    from icsa.faults.observability import Obs, all_cells, cell_key
    reasons, details, absent = [], [], []
    if not live.usable:
        absent.append("live classes: " + live.why_unusable())
    else:
        cl = live.data.get("classes") if isinstance(live.data, dict) else None
        if not isinstance(cl, dict):
            absent.append("live classes: no `classes` mapping")
            cl = {}
        details.append(f"live-recorded observability classes: {len(cl)}")
        starts = [calibration_started] if isinstance(calibration_started, str) else list(calibration_started or [])
        parsed = []
        for x in starts:
            try:
                t = dt.datetime.fromisoformat(x)
                if t.tzinfo is None:
                    raise ValueError("no time zone")
                parsed.append(t)
            except (TypeError, ValueError):
                absent.append(f"calibration run start time {x!r} is missing or not a zoned ISO time")
        if not starts:
            absent.append("no calibration run start time: cannot show the live classes were filed before the calibration")
        t0 = min(parsed) if parsed else None
        calibration_started = t0.isoformat() if t0 else None
        for k, v in cl.items():
            why = _live_problem(v)
            if why and why.startswith("MISSING: "):
                absent.append(f"live class {k}: {why[9:]}")
            elif why:
                reasons.append(f"live class {k}: {why}")
            elif t0 is not None and dt.datetime.fromisoformat(v["recorded_at"]) >= t0:
                reasons.append(f"live class {k}: recorded at {v['recorded_at']}, not before the first calibration run ({calibration_started})")
        need = [cell_key(*x[:5]) for x in all_cells({}) if x[5].obs is Obs.UNKNOWN_UNTIL_LIVE]
        unclassed = [k for k in need if k not in cl]
        if unclassed:
            absent.append(f"{len(unclassed)} of {len(need)} unknown_until_live cells not yet classed from the live check")
        details.append(f"unknown_until_live cells: {len(need)}, classed {len(need) - len(unclassed)}"
                       + (f"; first calibration run {calibration_started}" if calibration_started else ""))
    if not fault_cells.usable:
        absent.append("fault-injection rows: " + fault_cells.why_unusable())
    else:
        rows = [r for r in fault_cells.data if r.get("tested") is True and r.get("fault_type", "all") == "all"]
        applicable = {(x[2].value, x[1].value, x[3].value, x[4].value) for x in all_cells({}) if x[5].obs is not Obs.NOT_APPLICABLE}
        for o, rec in sorted({(o, rec) for o, _, rec, _ in applicable}):
            cells = [r for r in rows if r.get("option") == o and r.get("record") == rec
                     and (o, r.get("layout"), rec, r.get("condition", "cold")) in applicable]
            full = [r for r in cells if _complete_cell(r) is True]
            details.append(f"{o} x {rec}: {len(full)} complete cells of {len(cells)} with runs "
                           "(complete = every planned run of the cell scored)")
            if not cells:
                absent.append(f"no H3 row for option {o}, record {rec}")
            elif not full and any(_complete_cell(r) is None for r in cells):
                absent.append(f"option {o}, record {rec}: cell counts not recorded, cannot tell whether a complete cell exists")
            elif not full:
                best = max(cells, key=lambda r: (r.get("n_faulted") or 0) + (r.get("n_control") or 0))
                reasons.append(f"option {o}, record {rec}: no complete cell (best: {best.get('n_faulted') or 0} of "
                               f"{best.get('n_planned_faulted')} planned faulted runs, {best.get('n_control') or 0} of "
                               f"{best.get('n_planned_control')} planned fault-free, H3 status {best.get('status')})")
        n_full = sum(_complete_cell(r) is True for r in rows)
        st = [r.get("status") for r in rows]
        h3 = [r.get("meets_h3") for r in rows]
        details.append(f"H3 matrix (reported, never gated; the full matrix may continue after go): {n_full} of {len(applicable)} cells complete; "
                       f"status pass {st.count('pass')}, fail {st.count('fail')}, not testable {st.count('not_testable')}, "
                       f"incomplete {st.count('incomplete')}; meets_h3 true {sum(x is True for x in h3)}, false {sum(x is False for x in h3)}, "
                       f"no verdict {sum(x is None for x in h3)} of {len(rows)} rows")
    return _res(4, title, src, reasons, [live.evidence("live classes"), fault_cells.evidence("fidelity rows")], details, absent)


# ------------------------------------------------------------------ 5
def c5_pipeline(art: Artifact) -> CheckResult:
    title = "Scripted pipeline completes correctly through every option's path (#12)"
    src = SRC + " (v)"
    if not art.usable or not isinstance(art.data, dict):
        return missing(5, title, src, art)
    cells = {(c["option"], c["layout"]): c for c in art.data.get("cells", [])}
    reasons, details, absent = [], [], []
    for o in SCRIPTED_OPTIONS:
        for l in LAYOUTS:
            c = cells.get((o, l))
            if c is None:
                absent.append(f"{o} {l}: no scripted pipeline run")
            elif c.get("completed") is False or c.get("correct") is False:
                reasons.append(f"{o} {l}: completed={c.get('completed')} correct={c.get('correct')}")
            elif c.get("completed") is not True or c.get("correct") is not True:
                absent.append(f"{o} {l}: completed/correct not recorded")
            details.append(f"{o} {l}: " + ("absent" if c is None else f"completed={c.get('completed')}, correct={c.get('correct')}"))
    return _res(5, title, src, reasons, [art.evidence("scripted pipeline results")], details, absent)


# ------------------------------------------------------------------ 6
# The concurrency cap is PER BLOCK (science, #12, 1 Nov 17:30Z): block 1 is T, T-unpaginated, D and M in S1; block 2 is T, D and M
# in S2. Each block's cap is the highest level at which every cell of THAT block stays within 1.25 x its single-run wall time,
# with no errors, no OOM kill and within disk limits. The #12 lane's emitter writes `blocks["1"|"2"]` with `cap`, `wall_at_cap_s`
# and `cells`; the dossier recomputes each cap from the curves of that block's cells only and requires it to equal the declared one.
BLOCKS6 = {"1": [("T", "S1"), ("T-unpaginated", "S1"), ("D", "S1"), ("M", "S1")],
           "2": [("T", "S2"), ("D", "S2"), ("M", "S2")]}


DUTY_POINT_RULE = "duty-median"     # the `rule` a duty-cycle point carries (curve.DUTY_MEDIAN_RULE, copied by emit)
DUTY_RULE_NOTE = "duty points judged by 25(b) and 34; c6's registered-form check applies to registered points only"   # science, #34, 14:09Z


def concurrency_cap(cells: dict, ratio: float = 1.25):
    """Highest level at which every cell stays within `ratio` x its single-run time, with no errors, no OOM kill and
    within disk limits. Returns (cap | None, per-level notes). parameters.md, 'Concurrency cap'. A level counts only if its
    point says `oom_kills` is 0: an absent count is unknown, and unknown is not zero.

    A point of the duty-cycle curve (`rule` "duty-median", science #34, amendment 25(b)) is judged on the medians of its runs' ratios, each to its own
    host's reference: its `wall_ratio_ok` and `read_ratio_ok` carry that verdict, so the one comparison here that does not follow it, the point's worst
    wall against `ratio` x the single run (host a's), is skipped for it. Every other condition holds for it, and a point with no `rule` is judged as it was."""
    levels = None
    for c in cells.values():
        ls = {p["concurrency"] for p in c.get("curve", [])}
        levels = ls if levels is None else levels & ls
    ok = []
    for L in sorted(levels or []):
        good = True
        for c in cells.values():
            pt = next(p for p in c["curve"] if p["concurrency"] == L)
            single = c["single_run_wall_s"]
            if pt.get("wall_s") is None or single is None or (pt.get("rule") != DUTY_POINT_RULE and pt["wall_s"] > ratio * single) \
                    or pt.get("errors") != 0 or pt.get("within_disk") is not True or pt.get("oom_kills") != 0 \
                    or pt.get("wall_ratio_ok") is not True or pt.get("read_ratio_ok") is not True:
                good = False
        if good:
            ok.append(L)
    return (max(ok) if ok else None), ok


def _block_problems(name: str, art_data: dict) -> tuple[list[str], list[str], list[str], dict | None]:
    """(failures, missing, details, recomputed {cap, wall_at_cap_s}) for one block."""
    blocks = art_data.get("blocks")
    reasons, absent, details = [], [], []
    if not isinstance(blocks, dict):
        return reasons, [f"block {name}: the timing has no 'blocks' (the per-block cap format)"], details, None
    b = blocks.get(name)
    if not isinstance(b, dict) or b.get("stub"):
        return reasons, [f"block {name}: absent or a stub"], details, None
    cells = art_data.get("cells", {})
    keys = [f"{o}__{l}" for o, l in BLOCKS6[name]]
    for k in keys:
        c = cells.get(k)
        if not isinstance(c, dict):
            absent.append(f"block {name}: no timing cell {k}")
        elif c.get("single_run_wall_s") is None or c.get("provider_io_bytes") is None:
            absent.append(f"block {name}: {k}: wall time or provider I/O not measured")
        elif not c.get("curve"):
            absent.append(f"block {name}: no concurrency curve for {k}")
        else:
            details.append(f"{k}: single-run wall {c['single_run_wall_s']} s, provider I/O {c['provider_io_bytes']} B")
    if absent:
        return reasons, absent, details, None
    cap, _ = concurrency_cap({k: cells[k] for k in keys})
    declared = b.get("cap")
    wall = None
    if cap is not None:
        wall = max(next(p for p in cells[k]["curve"] if p["concurrency"] == cap)["wall_s"] for k in keys)
    details.append(f"block {name}: cap recomputed from its {len(keys)} cells: {cap}; declared: {declared}; "
                   f"wall at the cap {wall} s, declared {b.get('wall_at_cap_s')}")
    if declared is None:
        absent.append(f"block {name}: concurrency cap not set")
    if cap is None:
        reasons.append(f"block {name}: no concurrency level keeps every cell within 1.25 x its single-run time with no errors "
                       "and no OOM kill")
    elif declared is not None and declared != cap:
        reasons.append(f"block {name}: declared cap {declared} differs from the cap recomputed from its curves ({cap})")
    elif declared is not None and b.get("wall_at_cap_s") != wall:
        reasons.append(f"block {name}: declared wall_at_cap_s {b.get('wall_at_cap_s')} differs from the recomputed {wall}")
    return reasons, absent, details, {"cap": cap, "wall_at_cap_s": wall}


def c6_timing(art: Artifact) -> CheckResult:
    title = "Wall time and provider I/O measured; concurrency cap set per block (#12)"
    src = SRC + " (vi); cap rule: parameters.md 'Concurrency cap', per block (#12, 1 Nov 17:30Z)"
    if not art.usable or not isinstance(art.data, dict):
        return missing(6, title, src, art)
    reasons, details, absent = [], [], []
    for name in BLOCKS6:
        r, a, d, _ = _block_problems(name, art.data)
        reasons += r; absent += a; details += d
    cells = art.data.get("cells")
    if isinstance(cells, dict) and any(isinstance(p, dict) and p.get("rule") == DUTY_POINT_RULE
                                       for c in cells.values() if isinstance(c, dict) for p in (c.get("curve") or [])):
        details.append(DUTY_RULE_NOTE)      # science, #34, 14:09Z: stated wherever c6 and the cap rules are reported, once, when a duty point is present
    return _res(6, title, src, reasons, [art.evidence("scripted timing and curve")], details, absent)


def scripted_wall_at_cap(art: Artifact) -> float | None:
    """Term (b) of the time cap: the largest full-data run time at the block's cap over both blocks, each cap recomputed from
    that block's own cells (`wall_at_cap_s`, recomputed from the curves). None if either block is absent, a stub or has no cap, or when a block's declared cap or wall differs from the recomputed one: no
    silent resolution to either."""
    if not art.usable or not isinstance(art.data, dict):
        return None
    walls = []
    for name in BLOCKS6:
        r, a, _, rec = _block_problems(name, art.data)
        if r or a or rec is None or rec["cap"] is None or rec["wall_at_cap_s"] is None:
            return None
        walls.append(rec["wall_at_cap_s"])
    return max(walls)
