"""The values the parameter rules produce from the pilot (protocol/parameters.md, 'Rules').

Selected from RunRecords by block (pilot + calibration), finished or not, infra-failed attempts
included (an assumption stated to the parent). Integer arithmetic throughout.
"""
from __future__ import annotations

import dataclasses
import math

PROV_TOOL_ROUNDS, PROV_TOKENS, PROV_MIN = 150, 4_000_000, 240    # 'Provisional caps during the pilot'
CAP_TERMINATIONS = ("turn_cap", "token_budget", "time_cap")        # a run STOPPED by a cap; a run that reported first was not
BLOCKS = ("pilot", "calibration")


def ceil_to(x: int, m: int) -> int:
    return -(-x // m) * m


def rounds(rec: dict) -> int:
    """A round is one assistant message with one or more tool calls."""
    return sum(1 for t in rec.get("turns", []) if t.get("tool_calls"))


def total_tokens(rec: dict) -> int:
    return sum(t.get("input_tokens", 0) + t.get("output_tokens", 0) for t in rec.get("turns", []))


def turn_cap(max_rounds: int) -> int:
    return ceil_to(max(40, 2 * max_rounds), 10)


def token_budget(max_tokens: int) -> int:
    return ceil_to(3 * max_tokens, 10_000)


def time_cap_min(max_wall_s: float, scripted_wall_at_cap_s: float | None) -> tuple[int, bool]:
    """(minutes, term (b) included). (a) 2 x max pilot/calibration wall; (b) 2 x max scripted full-data
    time at the cap; the larger, rounded up to 10 min. Seconds are used so rounding is exact."""
    sec = 2 * max_wall_s
    if scripted_wall_at_cap_s is not None:
        sec = max(sec, 2 * scripted_wall_at_cap_s)
    minutes = -(-int(-(-sec // 1)) // 60)          # ceil seconds, then ceil minutes
    return ceil_to(minutes, 10), scripted_wall_at_cap_s is not None


BACKEND_NAMES = {"hpc": "site_a", "site_b": "site_b", "anthropic": "anthropic"}


def p95_nearest_rank(xs: list[float]) -> float:
    """The ceil(0.95 n)-th smallest value (nearest rank): with 20 values the 19th, with 5 the 5th."""
    s = sorted(xs)
    return s[math.ceil(0.95 * len(s)) - 1]


def wall_by_backend(rs: list[dict]) -> dict[str, dict]:
    """Wall time of the analysed pilot/calibration runs per model backend (site_a, site_b, anthropic):
    n, max and p95 (nearest rank); `few` is True when n < MIN_RUNS_PER_BACKEND (too few to judge). A run whose record names no backend is listed as 'unrecorded', never guessed."""
    g: dict[str, list[float]] = {}
    for r in rs:
        b = BACKEND_NAMES.get(r.get("backend") or "", "unrecorded" if not r.get("backend") else str(r["backend"]))
        g.setdefault(b, []).append(float(r["wall_time_s"]))
    return {b: {"n": len(v), "max_s": max(v), "p95_s": p95_nearest_rank(v), "few": len(v) < MIN_RUNS_PER_BACKEND}
            for b, v in sorted(g.items())}


MIN_RUNS_PER_BACKEND = 5      # fewer wall-time observations than this are "too few to judge"


@dataclasses.dataclass
class RuleValues:
    n_runs: int
    n_by_block: dict
    turn_cap: int | None
    token_budget: int | None
    time_cap_min: int | None
    max_rounds: int | None
    max_tokens: int | None
    max_wall_s: float | None
    scripted_b_included: bool
    notes: list
    cap_hit_cells: list
    wall_by_backend: dict = dataclasses.field(default_factory=dict)


def compute(records: list[dict], scripted_wall_at_cap_s: float | None, blocks=BLOCKS,
            include_infra_failed: bool = False) -> RuleValues:
    """Default: attempts that ended in an infrastructure failure are excluded from the maxima and reported
    apart (protocol/parameters.md line 38, 'Infrastructure failures': analysed attempt = the first that ends
    without an infrastructure failure; discarded attempts' tokens and time are reported per option)."""
    sel = [r for r in records if r.get("block") in blocks]
    rs = sel if include_infra_failed else [r for r in sel if not r.get("infra_failure")]
    notes: list[str] = []
    dropped = [r for r in sel if r not in rs]
    for o in sorted({r["run"]["option"] for r in dropped}):
        d = [r for r in dropped if r["run"]["option"] == o]
        notes.append(f"option {o}: {len(d)} infra-failed attempts excluded from the maxima (parameters.md line 38); discarded "
                     f"tokens {sum(total_tokens(r) for r in d)}, wall time {sum(r['wall_time_s'] for r in d):.0f} s")
    by = {b: sum(1 for r in rs if r.get("block") == b) for b in blocks}
    if not rs:
        return RuleValues(0, by, None, None, None, None, None, None, False, notes + ["no analysed pilot or calibration run: values undefined"], [])
    mr = max(rounds(r) for r in rs)
    mt = max(total_tokens(r) for r in rs)
    mw = max(r["wall_time_s"] for r in rs)
    incomplete = [r for r in rs if r.get("usage_complete") is False]
    if incomplete:
        notes.append(f"{len(incomplete)} runs have usage_complete false: their token totals are lower bounds, so the token budget is a lower bound")
    if by.get("calibration", 0) != 42:
        notes.append(f"{by.get('calibration', 0)} calibration runs present, 42 expected (parameters.md): the values are not final")
    # A provisional-cap hit is counted by termination (science ruling, #18, 1 Nov 16:01Z): the cap stopped the run. A run that
    # reported before reaching it was not stopped by it, however long it ran. The measured maxima are reported beside it.
    stopped = [r for r in rs if r.get("termination") in CAP_TERMINATIONS]
    hits = sorted({(r["run"]["model"], r["run"]["option"], r["run"]["layout"]) for r in stopped})
    if hits:
        by_cell: dict[tuple, set] = {}
        for r in stopped:
            by_cell.setdefault((r["run"]["model"], r["run"]["option"], r["run"]["layout"]), set()).add(r["termination"])
        notes.append(f"{len(hits)} cells hit a provisional cap: double that cap once and repeat the whole cell; these values are not final "
                     f"(stopped by: " + "; ".join(f"{'/'.join(c)} {'+'.join(sorted(t))}" for c, t in sorted(by_cell.items()))
                     + f"; measured maxima: tool rounds {mr}, total tokens {mt}, wall {mw:.0f} s)")
    tc, b_in = time_cap_min(mw, scripted_wall_at_cap_s)
    if not b_in:
        notes.append("time cap term (b), the scripted full-data time at the concurrency cap (#12), is missing: the value is a lower bound")
    wb = wall_by_backend(rs)
    few = [b for b, v in wb.items() if v["n"] < MIN_RUNS_PER_BACKEND]
    if few:
        notes.append("wall time per backend: too few to judge (fewer than "
                     f"{MIN_RUNS_PER_BACKEND} runs): " + ", ".join(f"{b} n={wb[b]['n']}" for b in few))
    return RuleValues(len(rs), by, turn_cap(mr), token_budget(mt), tc, mr, mt, mw, b_in, notes, hits, wb)
