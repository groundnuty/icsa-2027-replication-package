"""The frozen instance design (science decision on #5, June-August, seed 20271).

Input: `counts[(region, year)]` = reference events of that region's Jun-Aug of
that year, for every region and year in 2003..2022. Output: 50 `Pick`s.

DRAW ORDER of the one RNG, `numpy.random.default_rng(SEED)` (changing the order
changes the draw):
 1. Event-free set, repeated until both constraints hold (redraws counted):
      a. `rng.choice(eligible_regions, 8, replace=False)`, eligible = regions with
         >= 1 event-free year, ascending; the result order is the draw order;
      b. for each chosen region in that order: `rng.choice(its event-free years)`
         (years ascending); constraint: <= 3 picks in one year.
    Constraint "<= 1 per region" holds by (a).
 2. For each event-free region in draw order: its second period =
    `rng.choice(its event-bearing years)` (ascending; a different year by construction).
 3. For every other region, ascending: `rng.choice(event-bearing years, 2, replace=False)`.
 Instances are then sorted by (region, year) and numbered I00..I49.
 4. Pilot: `rng.choice(event-free instance ids, 2, replace=False)`; then
    `rng.choice(regions not used, 8, replace=False)` (ascending list); for each such region,
    in that order, `rng.choice` of its two instance ids (both event-bearing: a non-free region).
 5. Calibration: no draw (event-bearing pilot instance closest to the pilot median; ties: lower count, then lowest id).
 6. WAN anchors: `rng.choice(pilot event-free ids, 1)`, then `rng.choice(pilot event-bearing ids, 2, replace=False)`.
"""
from __future__ import annotations

import dataclasses

import numpy as np

SEED = 20271
YEARS = tuple(range(2003, 2023))
N_FREE = 8
MAX_PER_YEAR = 3
MAX_REDRAWS = 100_000   # a draw that fails this often is infeasible, not unlucky


@dataclasses.dataclass(frozen=True)
class Pick:
    instance_id: str
    region: int
    year: int
    events: int
    pilot: bool = False
    calibration: bool = False
    wan: bool = False

    @property
    def event_free(self) -> bool:
        return self.events == 0


@dataclasses.dataclass(frozen=True)
class Design:
    picks: list[Pick]
    redraws: int


def design(counts: dict[tuple[int, int], int], n_regions: int = 25, seed: int = SEED) -> Design:
    rng = np.random.default_rng(seed)
    free = {r: [y for y in YEARS if counts[(r, y)] == 0] for r in range(n_regions)}
    bearing = {r: [y for y in YEARS if counts[(r, y)] > 0] for r in range(n_regions)}
    eligible = [r for r in range(n_regions) if free[r]]
    if len(eligible) < N_FREE:
        raise ValueError("fewer eligible regions than the event-free quota")
    redraws = 0
    while True:
        regs = [int(r) for r in rng.choice(eligible, N_FREE, replace=False)]
        yrs = [int(rng.choice(free[r])) for r in regs]
        if max(yrs.count(y) for y in set(yrs)) <= MAX_PER_YEAR:
            break
        redraws += 1
        if redraws > MAX_REDRAWS:
            raise ValueError("the per-year cap cannot be met by the event-free years")
    sel: list[tuple[int, int]] = list(zip(regs, yrs))
    for r in regs:
        sel.append((r, int(rng.choice(bearing[r]))))
    for r in range(n_regions):
        if r not in regs:
            sel += [(r, int(y)) for y in rng.choice(bearing[r], 2, replace=False)]
    sel.sort()
    ids = {p: f"I{k:02d}" for k, p in enumerate(sel)}
    ev = {p: counts[p] for p in sel}
    free_ids = [ids[p] for p in sel if ev[p] == 0]
    by_region: dict[int, list[str]] = {}
    for p in sel:
        by_region.setdefault(p[0], []).append(ids[p])
    pilot_free = [str(i) for i in rng.choice(free_ids, 2, replace=False)]
    used_regions = {p[0] for p in sel if ids[p] in pilot_free}
    others = [r for r in range(n_regions) if r not in used_regions]
    pilot_regions = [int(r) for r in rng.choice(others, 8, replace=False)]
    pilot_bearing = []
    for r in pilot_regions:
        cand = [i for i in by_region[r] if ev[next(p for p in sel if ids[p] == i)] > 0]
        pilot_bearing.append(str(rng.choice(cand)))
    pilot = set(pilot_free) | set(pilot_bearing)
    evid = {ids[p]: ev[p] for p in sel}
    # calibration (science, #5): the event-bearing pilot instance whose count is closest to the median of
    # the 10 pilot counts; ties go to the lower count, then the lowest id. Never raises.
    med = float(np.median([evid[i] for i in pilot]))
    calib = min(pilot_bearing, key=lambda i: (abs(evid[i] - med), evid[i], i))
    wan_free = str(rng.choice(pilot_free))
    wan_bearing = [str(i) for i in rng.choice(sorted(pilot_bearing), 2, replace=False)]
    wan = {wan_free, *wan_bearing}
    picks = [Pick(ids[p], p[0], p[1], ev[p], ids[p] in pilot, ids[p] == calib, ids[p] in wan) for p in sel]
    return Design(picks, redraws)
