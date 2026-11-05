"""M skip-ahead for levels above 16 (the lead's ruling on #34, 2 Nov, option (i)): the curve's mix keeps M's 16-mount cap without waiting.

science's ruling: M x 16 was shown on site_g; more M sandboxes at once are not. The registered curve's levels are at most 16, where this module does
nothing (a level at or below 16 runs exactly as before). Above 16, each HOST holds a local counter of M sandboxes up, capped at its share: the
number of its M slot users (`ICSA_SLOT_KEYS` and the slot map, filtered to option M). The hosts' slot users partition the 16, so no coordination
between hosts is needed: the sum of the shares is at most 16.

A slot's counted cells are still the block's cells, each once, in the order `plans.mix_slots` gave it; the gate changes only the ORDER they run in:
- the next cell is M and the host is at its share: the slot runs its next non-M cell first, and asks again after it. The deferral is recorded on
  the M cell's run record (`extra["m_deferral"]`: the cell, when it was deferred, how long, the cells that ran instead);
- only M cells are left and the host is at its share: the slot waits for an M to free. That wait is idle (`idle_s` in the same record): the slot
  is not part of the level's full concurrency meanwhile;
- padding never starts an M cell beyond the share, nor while a counted slot is waiting for an M (counted runs first); a padding draw that would is
  skipped for the next draw.
Every record of an M run carries `extra["m_gate"]["start_epoch"]`; with its `total_s` that is the run's interval, from which the level's report
(`m_report`) measures the most M sandboxes up at once per host and in total. The measure comes from the records, not from the counter.
"""
from __future__ import annotations

import threading
import time
from typing import Iterator

from ..sandbox import termination
from . import plans

MAX_M_RUNS = plans.M_MOUNTS_PROVEN   # science's ruling: M x 16 was shown on site_g (the same number bounds the curve's top level, plans.DUTY_MAX_LEVEL)
M_OPTIONS = ("M", "M+")


def active(level: int) -> bool:
    """The gate is for levels above the registered curve's range; at or below 16 nothing here runs."""
    return level > plans.MAX_LEVEL


def is_m(plan) -> bool:
    return plan.option.value in M_OPTIONS


def block_has_m(block: int) -> bool:
    return any(o.value in M_OPTIONS for o, _ in plans.BLOCK_CELLS[block])


def host_m_share() -> int:
    """This host's M share: its M slot users, by its own `ICSA_SLOT_KEYS` and the slot map (the pool `tokens` leases from)."""
    from ..harness.slot_lease import SlotPool
    return len(SlotPool().slots_of("M"))


def m_shares(slot_keys: dict[str, list[str]], slot_map_path=None) -> dict[str, int]:
    """host -> its M share, from each host's slot keys and the slot map: for the launcher's check before a level, as a part computes its own."""
    from ..harness import slot_lease as SL
    m = SL.load_slot_map(slot_map_path or SL.SLOT_MAP)
    return {h: sum(1 for k in keys if k in m and m[k].option == "M") for h, keys in slot_keys.items()}


def gate_for(block: int, level: int, share: int | None = None) -> "MGate | None":
    """The level's gate on this host, or None at or below 16. A host with no M slot user whose mix has M cannot run them: refused, not waited for."""
    if not active(level):
        return None
    share = min(host_m_share() if share is None else int(share), MAX_M_RUNS)
    if block_has_m(block) and share < 1:
        raise SystemExit(f"block {block} level {level}: this host has no M slot user (its M share is 0), but every slot of the mix runs an M cell: refused")
    return MGate(share)


class MGate:
    """The host's M counter and what the level did with it. Thread-safe."""

    def __init__(self, share: int):
        self.share = int(share)
        self._cv = threading.Condition()
        self.up = 0
        self.pending = 0                 # counted slots whose M cell is deferred or waiting: padding defers to them
        self.padding_skipped = 0
        self.records: list[dict] = []    # the records of every run of the level on this host, counted and padding

    def try_acquire(self) -> bool:
        with self._cv:
            if self.up < self.share:
                self.up += 1
                return True
            return False

    def acquire_wait(self) -> float:
        """Blocks until an M is free on this host and takes it; the seconds waited. A SIGTERM ends the wait."""
        t0 = time.monotonic()
        with self._cv:
            while self.up >= self.share:
                if termination.requested():
                    raise SystemExit(termination.EXIT_CODE)
                self._cv.wait(0.2)
            self.up += 1
        return time.monotonic() - t0

    def release(self) -> None:
        with self._cv:
            self.up -= 1
            self._cv.notify_all()

    def _pend(self, delta: int) -> None:
        with self._cv:
            self.pending += delta

    def padding_start(self, plan) -> tuple[bool, dict]:
        """(run it?, its extra). An M draw beyond the share, or while a counted slot waits for an M, is skipped."""
        if not is_m(plan):
            return True, {}
        with self._cv:
            if self.up < self.share and not self.pending:
                self.up += 1
                return True, {"m_gate": {"start_epoch": time.time()}}
            self.padding_skipped += 1
        time.sleep(0.005)                # a block whose every draw is M must not spin
        return False, {}

    def padding_end(self, plan) -> None:
        if is_m(plan):
            self.release()

    def note(self, rec: dict | None) -> None:
        """Keeps the record of a run of the level (any cell, counted or padding) for the level's report."""
        if rec:
            with self._cv:
                self.records.append(rec)

    def report(self, host: str = "local") -> dict:
        r = m_report(self.records, {host: self.share})
        r["padding_m_skipped"] = self.padding_skipped
        return r


def cells(gate: MGate | None, slot: int, plan_list: list) -> Iterator[tuple[int, object, dict]]:
    """A slot's counted cells as (index, plan, extra to add): without a gate exactly the plans in their order, nothing added. With one, the M
    skip-ahead above; the M cell holds this host's M counter from just before it starts to just after it ends (the caller's loop body)."""
    if gate is None:
        for i, p in enumerate(plan_list):
            yield i, p, {}
        return
    todo = list(plan_list)
    deferral: dict | None = None         # the M cell at the head of `todo`, if it has been deferred
    i = 0
    try:
        while todo:
            head, hold = todo[0], False
            take = None
            if not is_m(head):
                take = todo.pop(0)
            elif gate.try_acquire():
                take, hold = todo.pop(0), True
            else:
                if deferral is None:
                    deferral = {"cell": head.key(), "deferred_at_epoch": time.time(), "ran_instead": [], "idle_s": 0.0}
                    gate._pend(1)
                alt = next((j for j, q in enumerate(todo) if j > 0 and not is_m(q)), None)
                if alt is not None:
                    take = todo.pop(alt)
                    deferral["ran_instead"].append(take.key())
                else:
                    deferral["idle_s"] += round(gate.acquire_wait(), 3)       # only M cells are left: an idle wait, recorded
                    take, hold = todo.pop(0), True
            extra: dict = {}
            if hold:
                start = time.time()
                extra["m_gate"] = {"start_epoch": start}
                if deferral is not None:
                    deferral["deferred_s"] = round(start - deferral["deferred_at_epoch"], 3)
                    extra["m_deferral"] = deferral
                    deferral = None
                    gate._pend(-1)
            try:
                yield i, take, extra
            finally:
                if hold:
                    gate.release()
            i += 1
    finally:
        if deferral is not None:
            gate._pend(-1)


def _max_overlap(intervals: list[tuple[float, float]]) -> int:
    """The most intervals open at once (half-open: one that ends when another starts does not overlap it)."""
    ev = sorted([(s, 1) for s, _ in intervals] + [(e, -1) for _, e in intervals], key=lambda x: (x[0], x[1]))
    up = peak = 0
    for _, d in ev:
        up += d
        peak = max(peak, up)
    return peak


def m_report(records: list[dict], shares: dict[str, int]) -> dict:
    """The level's M gate, from the run records of ALL its runs (every cell, counted and padding).

    Concurrency is measured from the records, not from the counter: each M run's interval is [`extra.m_gate.start_epoch`, + `total_s`] (the gate's
    start is before the run's own clock starts, so the interval never ends later than the gate let go), grouped by `extra.host` ("local" on one
    host). `within_share` is false when any host had more M up than its share, the total more than 16, or an interval could not be measured:
    unknown is not within.

    `cells`/`m_share_achieved`: M cells over all cells run, counted runs and padding apart. `longest_deferral`: the longest an M cell waited to
    start after it was first deferred, with its slot and cell (None when none was deferred)."""
    ivs: list[tuple[str, float, float]] = []
    unmeasured = 0
    n = {"counted": 0, "counted_m": 0, "padding": 0, "padding_m": 0}
    deferrals: list[tuple[dict, object]] = []
    for r in records:
        ex = r.get("extra") or {}
        kind = "padding" if ex.get("padding") else "counted"
        is_m_run = r.get("option") in M_OPTIONS
        n[kind] += 1
        n[kind + "_m"] += is_m_run
        start = (ex.get("m_gate") or {}).get("start_epoch")
        if not is_m_run or start is None:
            continue
        total = r.get("total_s")
        if isinstance(total, bool) or not isinstance(total, (int, float)) or total != total or total < 0:
            unmeasured += 1
            continue
        ivs.append((ex.get("host", "local"), float(start), float(start) + float(total)))
        if ex.get("m_deferral"):
            deferrals.append((ex["m_deferral"], ex.get("slot")))
    hosts = sorted({h for h, _, _ in ivs} | set(shares))
    per_host = {h: _max_overlap([(s, e) for hh, s, e in ivs if hh == h]) for h in hosts}
    total = _max_overlap([(s, e) for _, s, e in ivs])
    within = not unmeasured and total <= MAX_M_RUNS and all(per_host[h] <= shares.get(h, 0) for h in hosts)
    longest = max(deferrals, key=lambda d: d[0].get("deferred_s", 0.0), default=None)
    frac = lambda m, a: round(m / a, 4) if a else None      # noqa: E731
    return {"share": dict(shares), "cells": dict(n), "m_cells": n["counted_m"], "m_runs": len(ivs),
            "m_share_achieved": {"counted": frac(n["counted_m"], n["counted"]), "padding": frac(n["padding_m"], n["padding"])},
            "max_concurrent_m": {**per_host, "total": total},
            "deferrals": len(deferrals), "deferred_s": round(sum(d.get("deferred_s", 0.0) for d, _ in deferrals), 3),
            "idle_s": round(sum(d.get("idle_s", 0.0) for d, _ in deferrals), 3),
            "longest_deferral": None if longest is None else {"deferred_s": longest[0].get("deferred_s", 0.0), "slot": longest[1], "cell": longest[0].get("cell")},
            "unmeasured": unmeasured, "within_share": within}
