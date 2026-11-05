"""Scoring a detector output against the injected omission, and the tables built from it.

The platform_record dict is what #14's `fault_injection_adapter` reads (`fault_injected`,
`fault_detected`). That adapter groups by option only, so rows from the two records of one option
(audit and traefik/perf) and from different cache conditions would be MIXED: #14 must group and
filter on `record_type`, `condition`, `fault_type` and `observable_by_design` before it builds a
table (reported in the final report). The block name is distinct from the campaign's agent-run blocks.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from icsa.records import Layout, Option, RunId

from .detector import DetectorOutput
from .observability import RECORDS_OF, Obs, classify
from .records.base import AccessEvent, Kind, Record
from .scenarios import Condition, Fault, Injection, Scenario

BLOCK = "fault_injection"     # not in #14's [blocks].never; carries no campaign block of its own


@dataclasses.dataclass
class FaultRun:
    scenario: Scenario
    record: Record
    injection: Injection
    output: DetectorOutput | None          # None when the run could not be scored
    excluded_reason: str | None = None
    content: dict = dataclasses.field(default_factory=dict)
    matrix: object | None = None           # ledger.MatrixClaim of the calibration this run belongs to
    masking: object | None = None          # masking.Masking sealed in the plan (observable_per_instance cells)

    @property
    def cell_obs(self) -> Obs:
        return classify(self.scenario.fault, self.scenario.layout, self.scenario.option,
                        self.record, self.scenario.condition).obs

    @property
    def obs(self) -> Obs:
        """The cell's class; in an observable_per_instance cell, this run's sealed verdict (masked = unobservable)."""
        c = self.cell_obs
        if c is not Obs.PER_INSTANCE:
            return c
        if self.masking is None:
            raise ValueError(f"{self.scenario.sid} ({self.record.value}) is in an observable_per_instance cell: "
                             "it needs the masking verdict sealed in the plan")
        return Obs.UNOBSERVABLE if self.masking.masked else Obs.OBSERVABLE

    def _served(self) -> frozenset:
        """Omitted units the option's client serves whole, on a byte-level record (traefik, perf): unobservable by design,
        out of unit tp and fn, counted in the served share. The audit log has no bytes: nothing is 'served' there."""
        if self.record not in (Record.TRAEFIK, Record.PERF):
            return frozenset()
        if self.masking is None:
            raise ValueError(f"{self.scenario.sid} ({self.record.value}) is a byte-level run: it needs the masking verdict "
                             "sealed in the plan (matrix.seal_masking)")
        return frozenset(self.masking.served_omitted)

    @property
    def client_masked(self) -> bool:
        """Every omitted unit served whole by the client, on a byte-level record (the masked-run share)."""
        sv = self._served()
        return bool(self.injection.omitted) and bool(sv) and sv >= (self.injection.unread | self.injection.header_only)

    @property
    def detected(self) -> bool | None:
        """Run level (science, #11, 22:23Z): a faulted run is detected iff a NON-SERVED omitted unit is flagged (a flag
        on a unit that was not omitted is no detection); a control is an alarm iff anything is flagged."""
        if not self.scored:              # not observed, ambiguous or a short read: never a detection, never a clean control
            return None
        miss = self.output.missing
        if not self.injection.omitted:
            return bool(miss)
        return bool(miss & (self.injection.omitted - self._served()))

    @property
    def false_flags(self) -> frozenset:
        """Flagged days that were not omitted. A flag on an omitted day the client served is neither true nor false."""
        return self.output.missing - self.injection.omitted if self.scored else frozenset()

    @property
    def false_flag_only(self) -> bool:
        """A faulted run whose flags are all wrong: at least one false flag and no true one (it counts against precision)."""
        return bool(self.injection.omitted) and self.detected is False and bool(self.false_flags)

    @property
    def scored(self) -> bool:
        return self.output is not None and self.excluded_reason is None

    def counts(self, full: bool = False) -> tuple[int, int, int]:
        """tp, fp, fn over units (science, #11, 22:53Z). fp = flagged units that were not omitted, on faulted runs and
        controls alike. Default (the tested `observable` rows): omitted units the client served whole are out of tp and
        fn (unobservable by design; a flag on one is not false either). `full=True` (the reported-only `all` rows): the
        full denominator, every omitted unit, served ones included (as registered under v1: a served unit not flagged is
        a miss)."""
        om, miss = self.injection.omitted, (self.output.missing if self.output else frozenset())
        sv = frozenset() if full else self._served()
        return len((miss & om) - sv), len(miss - om), len(om - miss - sv)

    def platform_record(self) -> dict:
        tp, fp, fn = self.counts() if self.scored else (None, None, None)
        return {
            "fault_injected": bool(self.injection.omitted),
            "fault_detected": self.detected,
            "record_type": self.record.value, "fault_type": self.scenario.fault.value,
            "condition": self.scenario.condition.value,
            "observable_by_design": {Obs.OBSERVABLE: True, Obs.UNOBSERVABLE: False}.get(self.obs),
            "observability": self.obs.value, "cell_observability": self.cell_obs.value,
            "masked_by_client": self.masking.masked if self.masking is not None else None,
            "units_served_by_client": len(self._served()),
            "units_omitted": len(self.injection.omitted), "units_flagged": len(self.output.missing) if self.scored else None,
            "unit_tp": tp, "unit_fp": fp, "unit_fn": fn,
            "detector_fingerprint": self.output.fingerprint if self.output else None,
            "excluded_reason": self.excluded_reason, "scenario": self.scenario.sid, "block": BLOCK,
            "matrix_id": getattr(self.matrix, "matrix_id", None), "matrix_sha": getattr(self.matrix, "sha", None),
        }


@dataclasses.dataclass
class AdapterRow:
    """Duck-typed for #14's fault_injection_adapter (run.option, run.layout, block, platform_record)."""
    run: RunId
    platform_record: dict
    block: str = BLOCK
    exclude_from_analysis: bool = False


def adapter_rows(runs: Iterable[FaultRun], instance_id: str) -> list[AdapterRow]:
    out = []
    for r in runs:
        if not r.scored:
            continue
        s = r.scenario
        out.append(AdapterRow(RunId(instance_id, s.option, s.layout, "scripted", s.replicate), r.platform_record()))
    return out


def content_summary(events: Sequence[AccessEvent]) -> dict:
    """What the record contained for a run: events by kind, distinct targets, bytes asked/served."""
    kinds: dict[str, int] = {}
    for e in events:
        kinds[e.kind.value] = kinds.get(e.kind.value, 0) + 1
    return {"n_events": len(events), "by_kind": kinds,
            "distinct_targets": len({e.target for e in events if e.target}),
            "has_offsets": any(e.offset is not None for e in events),
            "has_range": any(e.range_header for e in events)}


# ---- statistics ---------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return float(max(0.0, c - h)), float(min(1.0, c + h))


def _ratio_ci(num: np.ndarray, den: np.ndarray, B: int, seed: int) -> tuple[float, float, float]:
    """Pooled ratio sum(num)/sum(den) over runs, with a cluster (run) bootstrap 95% interval."""
    if den.sum() == 0:
        return (float("nan"),) * 3
    pt = num.sum() / den.sum()
    rng = np.random.default_rng(seed)
    n = len(num)
    idx = rng.integers(0, n, size=(B, n))
    d = den[idx].sum(axis=1)
    ok = d > 0
    r = num[idx].sum(axis=1)[ok] / d[ok]
    return float(pt), float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def fidelity_table(runs: Sequence[FaultRun], subset: str = "all", per_fault: bool = False,
                   B: int = 2000, seed: int = 20271) -> pd.DataFrame:
    """Recall and precision per option x layout x record x condition (x fault type).

    Run level: recall = detected / faulted (Wilson), where a faulted run is detected iff a NON-SERVED omitted day
    is flagged (science, #11, 22:23Z); precision = true flags / all flags (Wilson; science, #2, 2 Nov), where a flag is a
    run: runs with a true flag / (those + faulted runs with only false flags + controls with any flag). A run with both
    counts as true (`n_true_and_false_flag`; its false days are in `unit_fp_faulted` and the unit precision). A flag only
    on an omitted day the client served is neither. False-alarm rate on the controls. A false flag on a faulted run the
    subset drops stays out of the tested precision, as registered, and is counted in `n_false_flag_unobservable`.
    Unit level (pooled, cluster bootstrap over runs): recall = flagged
    non-served omitted days / non-served omitted days, precision = flagged omitted days / flagged days.
    subset="observable" keeps only faulted runs that are OBSERVABLE by design (in a per-instance cell: not masked);
    controls stay, so precision keeps its meaning. Unit recall in the tested `observable` rows is over non-served
    omitted units; the reported-only `all` rows take the full denominator, served units included (science, #11,
    22:53Z). Flags on units that were not omitted are unit false positives, on faulted runs (`unit_fp_faulted`) beside
    the controls (`unit_fp_control`). Every row carries both masked shares over the group's faulted
    runs, `masked_share` (runs fully masked) and `served_unit_share` (omitted days served anyway); `check_shares`
    refuses a table that shows a recall without them.
    """
    rows = []
    sc = [r for r in runs if r.scored]
    key = lambda r: (r.scenario.option.value, r.scenario.layout.value, r.record.value, r.scenario.condition.value)
    for k in sorted({key(r) for r in sc}):
        cell = [r for r in sc if key(r) == k]
        ctrl = [r for r in cell if not r.injection.omitted]
        faulted = [r for r in cell if r.injection.omitted]
        groups = [(None, faulted)]
        if per_fault:
            groups = [(f, [r for r in faulted if r.scenario.fault is f]) for f in sorted({r.scenario.fault for r in faulted}, key=lambda x: x.value)]
        for f, site_g in groups:
            # both masked shares, over ALL faulted runs of the group (before the subset filter): 0 where no client masks
            n_masked = sum(r.client_masked for r in site_g)
            served_units = sum(len(r._served()) for r in site_g)
            om_units = sum(len(r.injection.omitted) for r in site_g)
            n_pi = sum(r.cell_obs is Obs.PER_INSTANCE for r in site_g)
            n_all = len(site_g)
            dropped: list[FaultRun] = []
            if subset == "observable":
                dropped = [r for r in site_g if r.obs is not Obs.OBSERVABLE]
                site_g = [r for r in site_g if r.obs is Obs.OBSERVABLE]
            if not site_g and not ctrl:
                continue
            tp = sum(bool(r.detected) for r in site_g)
            ff = sum(r.false_flag_only for r in site_g)
            fa = sum(bool(r.detected) for r in ctrl)
            flagged = tp + ff + fa
            pr = tp / flagged if flagged else float("nan")
            rl, rh = wilson(tp, len(site_g)); pl, ph = wilson(tp, flagged); al, ah = wilson(fa, len(ctrl))
            full = subset == "all"            # reported-only rows: every omitted unit, served ones included
            u = np.array([r.counts(full) for r in site_g], dtype=float).reshape(-1, 3)
            ur = _ratio_ci(u[:, 0], u[:, 0] + u[:, 2], B, seed) if len(u) else (float("nan"),) * 3
            uc = np.array([r.counts(full) for r in ctrl], dtype=float).reshape(-1, 3)
            up_ = np.concatenate([u, uc]) if len(uc) else u            # false flags on faulted runs AND controls count
            up = _ratio_ci(up_[:, 0], up_[:, 0] + up_[:, 1], B, seed) if len(up_) else (float("nan"),) * 3
            rows.append({"option": k[0], "layout": k[1], "record": k[2], "condition": k[3],
                         "fault_type": f.value if f else "all", "subset": subset,
                         # H3 is tested on recall AND precision over the faults observable by design for this
                         # record (per option x layout x record); every other row is reported, never tested.
                         "tested": bool(subset == "observable" and f is None),
                         "n_faulted": len(site_g), "n_control": len(ctrl),
                         "recall": tp / len(site_g) if site_g else float("nan"), "recall_lo": rl, "recall_hi": rh,
                         "precision": pr, "precision_lo": pl, "precision_hi": ph,
                         "false_alarm": fa / len(ctrl) if ctrl else float("nan"), "fa_lo": al, "fa_hi": ah,
                         "n_false_flag_faulted": ff,
                         "n_true_and_false_flag": sum(bool(r.detected) and bool(r.false_flags) for r in site_g),
                         "n_false_flag_unobservable": sum(bool(r.false_flags) for r in dropped),
                         # unit-level false positives, beside the controls' alarms: flagged units that were not omitted
                         "unit_fp_faulted": int(u[:, 1].sum()) if len(u) else 0,
                         "unit_fp_control": int(uc[:, 1].sum()) if len(uc) else 0,
                         "unit_denominator": "all omitted units" if full else "non-served omitted units",
                         "unit_recall": ur[0], "unit_recall_lo": ur[1], "unit_recall_hi": ur[2],
                         "unit_precision": up[0], "unit_precision_lo": up[1], "unit_precision_hi": up[2],
                         "n_per_instance": n_pi, "masked_share": n_masked / n_all if n_all else float("nan"),
                         "served_unit_share": served_units / om_units if om_units else float("nan")})
    return check_shares(pd.DataFrame(rows))


SHARE_COLS = ("masked_share", "served_unit_share")


def check_shares(t: pd.DataFrame) -> pd.DataFrame:
    """No recall without both masked shares beside it (science, #11, 22:23Z): a table with a recall column must carry
    `masked_share` (faulted runs fully masked) and `served_unit_share` (omitted units served anyway), and every row
    that shows a recall must show both."""
    rcols = [c for c in t.columns if "recall" in c]
    if not rcols:
        return t
    missing = [c for c in SHARE_COLS if c not in t.columns]
    if missing:
        raise ValueError(f"a recall table without {missing}: both masked shares sit beside every recall")
    shown = t[rcols].notna().any(axis=1)
    bad = shown & t[list(SHARE_COLS)].isna().any(axis=1)
    if bad.any():
        raise ValueError(f"{int(bad.sum())} row(s) show a recall without both masked shares")
    return t


def record_content_table(runs: Sequence[FaultRun]) -> pd.DataFrame:
    """What the record contained, per fault type x layout x option x record x condition."""
    rows = []
    g: dict[tuple, list[FaultRun]] = {}
    for r in runs:
        s = r.scenario
        g.setdefault((s.fault.value, s.layout.value, s.option.value, r.record.value, s.condition.value), []).append(r)
    for k, rs in sorted(g.items()):
        c = [r.content for r in rs if r.content]
        pi = [r for r in rs if r.cell_obs is Obs.PER_INSTANCE and r.injection.omitted]
        rows.append({"fault_type": k[0], "layout": k[1], "option": k[2], "record": k[3], "condition": k[4],
                     "observability": rs[0].cell_obs.value, "n_runs": len(rs),       # the cell's class: order-free
                     "n_masked": sum(r.client_masked for r in rs), "n_per_instance_observable": sum(
                         r.obs is Obs.OBSERVABLE for r in pi),
                     "mean_events": float(np.mean([x["n_events"] for x in c])) if c else float("nan"),
                     "mean_distinct_targets": float(np.mean([x["distinct_targets"] for x in c])) if c else float("nan"),
                     "has_offsets": any(x["has_offsets"] for x in c), "has_range": any(x["has_range"] for x in c),
                     "mean_units_omitted": float(np.mean([len(r.injection.omitted) for r in rs])),
                     "mean_units_flagged": float(np.mean([len(r.output.missing) for r in rs if r.output] or [float("nan")]))})
    return pd.DataFrame(rows)


H3_THRESHOLD = 0.9


class IncompleteMatrix(RuntimeError):
    """A verdict was asked of a partial matrix: an incomplete cell is never a pass or a fail."""


_ALLOCATION_COLS = tuple(f"n_{s}_{k}" for s in ("invalid", "lost", "pending", "withheld") for k in ("faulted", "control"))


def h3_verdict(table: pd.DataFrame, claim=None) -> dict[str, str]:
    """{option.layout.record.condition: pass | fail | not_testable}. Raises IncompleteMatrix if any tested cell is incomplete
    (science, #2, 2 Nov: a partial matrix reports incomplete, and asking it for a verdict exits non-zero), if the table cannot
    show its allocation (one written before that rule), or, given the `claim`, if it lacks a cell of the plan or is another
    matrix's."""
    missing = [c for c in _ALLOCATION_COLS if c not in table.columns]
    if missing:
        raise IncompleteMatrix(f"the table does not show its allocation (no {missing[:2]}): no verdict; score it again")
    t = table[table["tested"].astype(bool)]
    if t.empty:
        raise IncompleteMatrix("no tested cell: nothing to give a verdict on")
    if claim is not None:
        if set(table["matrix_sha"]) != {claim.sha}:
            raise IncompleteMatrix(f"the table is not of the claimed matrix {claim.matrix_id}: no verdict")
        want = {k for sid in claim.planned for k in _sid_cells(sid)}
        have = {tuple(str(r[c]) for c in ("option", "layout", "record", "condition")) for _, r in t.iterrows()}
        if want - have:
            raise IncompleteMatrix(f"{len(want - have)} planned cell(s) have no row, first {sorted(want - have)[:2]}: no verdict")
    short = t[(t[list(_ALLOCATION_COLS)].sum(axis=1) > 0) & (t["status"] != "incomplete")]
    if len(short):
        raise IncompleteMatrix(f"{len(short)} tested cell(s) have a status without their whole allocation: no verdict")
    inc = t[t["status"] == "incomplete"]
    if len(inc):
        first = [".".join(str(r[c]) for c in ("option", "layout", "record", "condition")) for _, r in inc.head(3).iterrows()]
        raise IncompleteMatrix(f"{len(inc)} of {len(t)} tested cells are incomplete, first {first}: no verdict")
    bad = sorted(set(t["status"]) - {"pass", "fail", "not_testable"})
    if bad:
        raise ValueError(f"unknown status in a tested row: {bad}")
    return {".".join(str(r[c]) for c in ("option", "layout", "record", "condition")): r["status"] for _, r in t.iterrows()}


def _check_one_matrix(runs: Sequence[FaultRun]) -> None:
    """Runs that carry a matrix claim must all carry the same one, each planned run at most once."""
    shas = {getattr(r.matrix, "sha", None) for r in runs}
    if len(shas) > 1:
        raise ValueError(f"runs from more than one matrix (or some without one): {sorted(map(str, shas))}")
    if shas != {None}:
        seen = [(r.scenario.sid, r.record) for r in runs]
        if len(set(seen)) != len(seen):
            raise ValueError("a planned run appears twice: the matrix runs once")


def _ckey(r: FaultRun) -> tuple:
    return (r.scenario.option.value, r.scenario.layout.value, r.record.value, r.scenario.condition.value)


def _sid_cells(sid: str) -> list[tuple]:
    """The record cells a planned sid (fault.layout.option.condition.rN) belongs to: all records of its option."""
    fault, layout, option, cond, _ = sid.split(".")
    return [(option, layout, rec.value, cond) for rec in RECORDS_OF[Option(option)]]


_STATES = ("planned", "scored", "invalid", "lost", "withheld", "pending")


def _allocation(runs: Sequence[FaultRun], planned: Sequence[str], lost_sids: Sequence[str],
                withheld: Sequence[str]) -> dict[tuple, dict]:
    """Every planned run's state in each of its record cells: {cell: {state: [faulted, control], "why": Counter-like}}.

    scored: has a scored result. invalid: it ran and its record gives no result (not observed, ambiguous, a short read).
    lost: the ledger says it left no record to score. withheld: left out on purpose by the caller. pending: not run yet."""
    by = {(r.scenario.sid, r.record.value): r for r in runs}
    lost_, held = set(lost_sids), set(withheld)
    out: dict[tuple, dict] = {}
    for sid in planned:
        ctrl = sid.split(".")[0] == Fault.NONE.value
        for k in _sid_cells(sid):
            c = out.setdefault(k, {**{s: [0, 0] for s in _STATES}, "why": {}})
            c["planned"][ctrl] += 1
            r = by.get((sid, k[2]))
            if sid in held:
                state = "withheld"
            elif r is not None and r.scored:
                state = "scored"
            elif r is not None:
                state = "invalid"
                why = (r.excluded_reason or "no output").split(":")[0]
                c["why"][why] = c["why"].get(why, 0) + 1
            elif sid in lost_:
                state = "lost"
            else:
                state = "pending"
            c[state][ctrl] += 1
    return out


def h3_table(runs: Sequence[FaultRun], *, claim, lost_sids: Sequence[str] = (), withheld: Sequence[str] = (),
             B: int = 2000, seed: int = 20271) -> pd.DataFrame:
    """The H3 exhibit, per option x layout x record x condition, for every cell of the claimed plan.

    Tested rows (`tested` True, subset "observable"): recall and precision over the faults observable
    by design for that cell; `status` is
    - "pass": every planned run of the cell is scored and both point estimates >= 0.9 (intervals are reported, not used);
    - "fail": every planned run is scored and a point estimate is below it. Nothing flagged gives recall 0 and undefined
      precision, which fails;
    - "not_testable": the cell has no observable fault type (the audit log in S2) and every planned run is scored; metrics
      are NaN;
    - "incomplete": a planned run of the cell has no scored result, or no observable faulted run is scored. Never a
      pass or a fail (science, #2, 2 Nov: "every planned run is run once"); the numbers so far stay visible.
    Each row counts its planned runs (`n_planned_*`) and those without a result: `n_invalid_*` (ran, the record gives no
    result; `invalid_reasons` says why), `n_lost_*` (the ledger's lost sids), `n_pending_*` (not run yet), `n_withheld_*`
    (left out by the caller). `meets_h3` is True/False for pass/fail and None otherwise. `h3_verdict` refuses a table with
    an incomplete cell. Reported-only rows (recall over all faults, per fault type) follow with `tested` False and
    `status` "reported".
    """
    sc = [r for r in runs if r.scored]
    if claim is None or not getattr(claim, "sha", None):
        raise ValueError("calibration results need the matrix claim (matrix.calibration_plan / ledger)")
    planned = tuple(getattr(claim, "planned", ()) or ())
    if not planned:
        raise ValueError(f"matrix {getattr(claim, 'matrix_id', '?')}: the claim carries no planned runs, and a cell's "
                         "verdict needs its whole planned allocation")
    bad = [r.scenario.sid for r in sc if getattr(r.matrix, "sha", None) != claim.sha]
    if bad:
        raise ValueError(f"{len(bad)} run(s) are not from the claimed matrix {claim.matrix_id}, first {bad[:2]}")
    foreign = sorted({r.scenario.sid for r in runs} - set(planned))
    if foreign:
        raise ValueError(f"{len(foreign)} run(s) are not from the claimed matrix {claim.matrix_id}, first {foreign[:2]}")
    _check_one_matrix(sc)
    obs = fidelity_table(runs, "observable", False, B, seed)
    rows = []
    alloc = _allocation(runs, planned, lost_sids, withheld)
    for k in sorted(alloc):
        opt, layout, rec, cond = Option(k[0]), Layout(k[1]), Record(k[2]), Condition(k[3])
        a = alloc[k]
        cell = [r for r in sc if _ckey(r) == k]
        has_observable = any(classify(f, layout, opt, rec, cond).obs in (Obs.OBSERVABLE, Obs.PER_INSTANCE)
                             for f in Fault if f is not Fault.NONE)
        base = {"option": k[0], "layout": k[1], "record": k[2], "condition": k[3], "fault_type": "all",
                "subset": "observable", "tested": True,
                "n_faulted": sum(1 for r in cell if r.injection.omitted and r.obs is Obs.OBSERVABLE),
                "n_control": sum(1 for r in cell if not r.injection.omitted),
                "n_false_flag_faulted": 0, "n_true_and_false_flag": 0, "n_false_flag_unobservable": 0,
                "unit_fp_faulted": sum(len(r.false_flags) for r in cell if r.injection.omitted),
                "unit_fp_control": sum(len(r.false_flags) for r in cell if not r.injection.omitted)}
        whole = not any(sum(a[s]) for s in ("invalid", "lost", "withheld", "pending"))
        if not has_observable:      # never a verdict; but a record that lost runs here is still a partial matrix
            rows.append({**base, "status": "not_testable" if whole else "incomplete", "meets_h3": None})
            continue
        m = obs.iloc[0:0] if obs.empty else obs[(obs.option == k[0]) & (obs.layout == k[1]) & (obs.record == k[2])
                                                & (obs.condition == k[3])]
        r = base if m.empty else m.iloc[0].to_dict()
        if not whole or r["n_faulted"] == 0:
            rows.append({**r, "status": "incomplete", "meets_h3": None})
        else:
            ok = bool(r["recall"] >= H3_THRESHOLD and r["precision"] >= H3_THRESHOLD)   # NaN precision -> False
            rows.append({**r, "status": "pass" if ok else "fail", "meets_h3": ok})
    rest = pd.concat([fidelity_table(runs, "all", False, B, seed), fidelity_table(runs, "all", True, B, seed)],
                     ignore_index=True)
    rest["status"], rest["meets_h3"] = "reported", None
    t = pd.concat([pd.DataFrame(rows), rest], ignore_index=True)
    t["tested"] = t["tested"].astype(bool)
    for c in ("recall", "precision", "false_alarm", "unit_recall", "unit_precision", *SHARE_COLS):
        if c not in t.columns:
            t[c] = float("nan")       # every H3 row has them, NaN where undefined (science, #2, 2 Nov)
    kcols = ["option", "layout", "record", "condition"]
    cells = [alloc[tuple(r[c] for c in kcols)] for _, r in t.iterrows()]
    for state in ("planned", "invalid", "lost", "pending", "withheld"):
        t[f"n_{state}_faulted"] = [c[state][0] for c in cells]
        t[f"n_{state}_control"] = [c[state][1] for c in cells]
    t["invalid_reasons"] = [json.dumps(c["why"], sort_keys=True) if c["why"] else "" for c in cells]
    t["matrix_id"], t["matrix_sha"] = claim.matrix_id, claim.sha
    return check_shares(t)
