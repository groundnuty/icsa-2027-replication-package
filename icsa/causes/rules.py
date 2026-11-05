"""The rule coder (#17): a deterministic function of a RunEvidence. See codebook.py for the
codes and the precedence. Notation: R required extent, A analysed extent (#9 A_lo; none
recorded means nothing analysed), P read extent (None: not observed), M = R - A the
missing units, U = M - P the missing units that were never read.
"""
from __future__ import annotations

import dataclasses

import numpy as np

from icsa.extent import Extent, PartedExtent
from icsa.records import Layout, OmissionLabel, Termination

from . import codebook as cb
from .evidence import RunEvidence

CAP_CODE = {Termination.TIME_CAP: "time_cap", Termination.TURN_CAP: "turn_cap",
            Termination.TOKEN_BUDGET: "token_budget", Termination.OUTPUT_CAP: "output_cap",
            Termination.ERROR: "run_error"}

POP_OMITTING, POP_UNFINISHED, POP_INCORRECT = "omitting", "unfinished", "incorrect_complete"
SKIP_UNKNOWN_LABEL, SKIP_COMPLETE = "unknown_label", "complete_and_correct"


@dataclasses.dataclass(frozen=True)
class Coding:
    block: str
    run_key: str
    primary: str
    secondary: tuple[str, ...]
    attribution: str | None      # of truncated_listing, whether primary or secondary
    population: str
    trail: tuple[str, ...]       # why: the facts the rules used
    recovered_from_truncated_listing: bool | None = None   # see recovered_from_truncation
    listing_evidence_incomplete: bool = False

    @property
    def cause_detail(self) -> str:
        return self.primary + (f":{self.attribution}" if self.attribution and self.primary == "truncated_listing"
                               else "")


@dataclasses.dataclass(frozen=True)
class Skipped:
    block: str
    run_key: str
    reason: str                  # SKIP_*
    recovered_from_truncated_listing: bool | None = None
    listing_evidence_incomplete: bool = False


def population(ev: RunEvidence) -> str | None:
    """Which coded population the run belongs to, or None (not coded)."""
    if ev.infra_failure or not ev.finished:
        return POP_UNFINISHED
    if ev.label == OmissionLabel.OMITTING:
        return POP_OMITTING
    if ev.label == OmissionLabel.UNKNOWN:
        return None
    if ev.label == OmissionLabel.COMPLETE and ev.correct is False and ev.complete_extent:
        return POP_INCORRECT
    return None


# ---- geometry (day x cell units) ----

def _missing(req: PartedExtent, a: PartedExtent | None) -> PartedExtent:
    if a is None:
        return req
    return PartedExtent(req.baseline.minus(a.baseline), req.target.minus(a.target))


def _count(pe: PartedExtent) -> int:
    return pe.baseline.count() + pe.target.count()


def _whole_days(req_part: Extent, m_part: Extent) -> bool:
    """Every day with a missing unit lacks every required cell of that day."""
    if m_part.days.size == 0:
        return False
    idx = np.searchsorted(req_part.days, m_part.days)
    return bool(np.all(m_part.mask.sum(axis=(1, 2)) == req_part.mask[idx].sum(axis=(1, 2))))


def _cell_pattern(req: PartedExtent, m: PartedExtent) -> bool:
    """The same non-empty cell set is missing on every required day of both parts."""
    pats = []
    for r, mp in ((req.baseline, m.baseline), (req.target, m.target)):
        if r.days.size == 0:
            continue
        if not np.array_equal(r.days, mp.days):
            return False
        if not np.all(mp.mask == mp.mask[0]):
            return False
        pats.append(mp.mask[0])
    return bool(pats) and all(np.array_equal(pats[0], p) for p in pats) and bool(pats[0].any())


def _other_days(ev: RunEvidence) -> int:
    """How many days outside the required ones the run decoded or analysed: what can stand in for a missing day. Neither
    summary of what lay beyond will do (b3 #1). `read_beyond_units` counts extra cells on required days too, and
    `read_beyond_days` is about listings: a file fetched for its header or downloaded and never opened is in it, and on
    S2 it is always empty."""
    req = set(int(d) for d in ev.required.baseline.days) | set(int(d) for d in ev.required.target.days)
    days = {int(d) for d in (ev.read_other_days or ())}
    for pe in (ev.read, ev.analysed):
        if pe is not None:
            for e in (pe.baseline, pe.target):
                days |= {int(d) for d, n in zip(e.days, e.mask.sum(axis=(1, 2))) if n}
    return len(days - req)


def missing_cell_counts(req: PartedExtent, analysed: PartedExtent | None) -> tuple[int, int]:
    """(cells missing on every required day, cells missing on some of them but not all), over both parts: what tells
    `wrong_subset_region` from `read_not_used` without the extents. `_cell_pattern` is true exactly when the first is
    above zero and the second is zero."""
    m = _missing(req, analysed)
    n_days = req.baseline.days.size + req.target.days.size
    parts = [p.mask.sum(axis=0) for p in (m.baseline, m.target) if p.days.size]
    if not n_days or not parts:
        return 0, 0
    per_cell = sum(parts)
    return int((per_cell == n_days).sum()), int(((per_cell > 0) & (per_cell < n_days)).sum())


def _cut_listings(ev: RunEvidence) -> dict[str, dict]:
    """The directories whose listing stopped short of the directory size."""
    return {d: v for d, v in (ev.listing or {}).items()
            if v["truncated"] and not (v["dir_size"] is not None and v["entries_listed"] >= v["dir_size"])}


def _read_beyond_listed(ev: RunEvidence) -> bool | None:
    """Did the run read a data file beyond the union of the names it was listed? Day order of the
    names is the position in the directory (S1), so the union of the listed names is the longest
    listed prefix: the days below max(entries_listed). Read days are those of the read extent
    (required days); units outside the required set are only a count (`read_beyond_units`) with no
    day unless `read_beyond_days` gives them; without it, when there are some and no required-day read beyond the names
    proves recovery, the answer is None (unknown), never False. None also: read extent not observed."""
    if ev.listing is None:
        return None
    listed = max((v["entries_listed"] for v in ev.listing.values()), default=0)
    if ev.read_beyond_days is not None and any(int(d) >= listed for d in ev.read_beyond_days):
        return True                                  # proven by the non-required reads alone
    if ev.read is None:
        return None
    for e in (ev.read.baseline, ev.read.target):
        if e.days.size and bool(e.mask[e.days >= listed].any()):
            return True
    if ev.read_beyond_days is None and (ev.read_beyond_units or 0) > 0:
        return None
    return False


def recovered_from_truncation(ev: RunEvidence) -> bool | None:
    """The run's listings were truncated and it still read a data file beyond the names it was
    listed (it built names from the pattern, say): it escaped the truncation. Recorded for every
    run, whatever its outcome. False: no truncated listing (or not an S1 run). None: S1 listing or
    read extent not observed, or the listing disputed, in any layout."""
    if ev.listing_disagrees:                           # disputed listing: no recovery conclusion
        return None
    if ev.layout != Layout.S1:
        return False
    if ev.listing is None:
        return None
    if not _cut_listings(ev):
        return False
    return _read_beyond_listed(ev)


def listing_evidence_incomplete(ev: RunEvidence) -> bool:
    """A cut S1 listing, and reads outside the required days whose days are unknown, so recovery
    cannot be decided (flag None); or the tracer's and the gate's listings disagree, in any layout (#9, science
    16:56Z: a listing the in-process hook did not see). No listing conclusion is drawn. Counted, so these runs
    cannot vanish."""
    if ev.listing_disagrees:
        return True
    return (ev.layout == Layout.S1 and ev.listing is not None and bool(_cut_listings(ev))
            and _read_beyond_listed(ev) is None and ev.read_beyond_days is None
            and (ev.read_beyond_units or 0) > 0)


def _truncated_listing(ev: RunEvidence, u: PartedExtent) -> tuple[bool, str | None, str]:
    """(fires, attribution, why). Fires only if a listing was truncated, a required day lies
    beyond the listed names, and the run read no data file beyond the names it was listed. (The
    beyond-the-names clause alone is true of every required day in every run of the study: the first
    1,000 S1 entries end on 1984-09-26 and the first required day is 1992-05-12, entry 3,785.)"""
    if ev.listing is None:
        return False, None, "listing not observed"
    if ev.listing_disagrees:
        return False, None, "the tracer's and the gate's listings disagree: listing evidence incomplete"
    if ev.read is None:
        return False, None, "read not observed: cannot say the files beyond the page were never read"
    if ev.layout != Layout.S1:
        return False, None, "listing rule applies to S1 directories"
    beyond = _read_beyond_listed(ev)
    if beyond is None:
        return False, None, "reads outside the required days cannot be placed against the listed names"
    if beyond:
        return False, None, "read beyond the listed names: recovered from the truncated listing" \
            if _cut_listings(ev) else "complete listing"
    hit, attrs = [], []
    udays = np.union1d(u.baseline.days, u.target.days)
    for d, v in _cut_listings(ev).items():
        if udays.size and int(udays.max()) >= v["entries_listed"]:     # a required day beyond the listed names
            hit.append(d)
            attrs.append(v["attribution"] or "client")
    if not hit:
        return False, None, "no truncated listing with required files beyond it"
    return True, ("agent" if "agent" in attrs else "client"), f"truncated listing of {sorted(hit)}, nothing read beyond it"


def _chain(ev: RunEvidence, report_ended: bool) -> tuple[list[str], str | None, list[str]]:
    """Every access/analysis code that fires, in precedence order; the truncated_listing
    attribution; the facts. `report_ended`: the run ended with its final message (no cap)."""
    m = _missing(ev.required, ev.analysed)
    trail: list[str] = [f"missing_units={_count(m)}",
                        f"analysed={'none' if ev.analysed is None else 'recorded'}",
                        f"read={'not_observed' if ev.read is None else 'observed'}"]
    if _count(m) == 0:
        return [], None, trail
    if ev.read is None:
        u, rd = m, None            # cannot say what was read: nothing in M is known to have been read
    else:
        u = PartedExtent(m.baseline.minus(ev.read.baseline), m.target.minus(ev.read.target))
        rd = PartedExtent(m.baseline.minus(u.baseline), m.target.minus(u.target))
    out: list[str] = []
    attr = None

    ok, a, why = _truncated_listing(ev, u)
    trail.append(why)
    if ok:
        out.append("truncated_listing")
        attr = a

    # Shape rules and read_not_used compare an analysed extent with the required one. They need
    # a finished run with a recorded extent; otherwise there is no analysis to have gone wrong.
    shape_ok = ev.analysed is not None and ev.finished
    trail.append(f"shape_rules={'on' if shape_ok else 'off'}")
    if shape_ok:
        other = _other_days(ev)
        trail.append(f"other_days_outside_required={other}")
        b_whole = _whole_days(ev.required.baseline, m.baseline)
        t_whole = _whole_days(ev.required.target, m.target)
        b_any, t_any = m.baseline.count() > 0, m.target.count() > 0
        if t_any and t_whole and not b_any and other >= m.target.days.size:
            out.append("wrong_subset_period")
        if b_any and b_whole and not t_any and other >= m.baseline.days.size:
            out.append("wrong_subset_baseline")
        if ev.read is not None and _count(u) == 0 and _cell_pattern(ev.required, m):
            out.append("wrong_subset_region")

    if (ev.read is not None and _count(u) > 0) or (ev.truncated_downloads or 0) > 0:
        out.append("skipped_or_partial_read")
        if (ev.truncated_downloads or 0) > 0:
            trail.append(f"truncated_downloads={ev.truncated_downloads}")
    if shape_ok and rd is not None and _count(rd) > 0 and not (
            {"wrong_subset_period", "wrong_subset_baseline", "wrong_subset_region"} & set(out)):
        out.append("read_not_used")
    if report_ended and not out:
        out.append("early_stop")     # ended by itself, extent short, no rule says where it went
    # keep the codebook order
    out = sorted(dict.fromkeys(out), key=lambda c: (cb.RANK[c], cb.CODE_NAMES.index(c)))
    return out, attr, trail


def code_run(ev: RunEvidence) -> Coding | Skipped:
    pop = population(ev)
    rec = recovered_from_truncation(ev)
    if pop is None:
        why = SKIP_UNKNOWN_LABEL if ev.label == OmissionLabel.UNKNOWN else SKIP_COMPLETE
        return Skipped(ev.block, ev.run_key, why, rec, listing_evidence_incomplete(ev))
    sec_flags = (cb.MALFORMED_TOOL_CALLS,) if ev.invalid_tool_args_rounds > 0 else ()
    report_ended = ev.termination == Termination.REPORT
    chain, attr, trail = _chain(ev, report_ended)

    def done(primary, rest):
        sec = tuple(c for c in rest if c != primary) + sec_flags
        return Coding(ev.block, ev.run_key, primary, sec, attr if "truncated_listing" in (primary, *rest) else None,
                      pop, tuple(trail), rec, listing_evidence_incomplete(ev))

    if ev.infra_failure:
        trail.append(f"infra_reason={ev.infra_reason}")
        return done("infra_failure", chain)
    if ev.termination in CAP_CODE:
        trail.append(f"termination={ev.termination.value}")
        return done(CAP_CODE[ev.termination], chain)
    if chain:
        return done(chain[0], chain[1:])
    # nothing missing from the extent (or no evidence): only a wrong result can still be a cause
    if _count(_missing(ev.required, ev.analysed)) == 0 and ev.finished and ev.correct is False:
        trail.append(f"cf_computation_f1={ev.cf_computation_f1}")
        return done("analysis_error_on_covered_data", [])
    return done("unknown", [])
