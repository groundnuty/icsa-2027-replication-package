"""What gets run, and in what order. Pure functions: no I/O, unit-testable.

The provider's page cache cannot be cleared (no restarts or config changes on the federation), and all the pilot
instances share the 1,452 baseline days, so an earlier run warms the provider for a later one. The pilot order is
therefore a seeded permutation of all runs: no option or layout is systematically first.
"""
from __future__ import annotations

import numpy as np

from ..records import Layout, Option
from .runner import Plan

PILOT = ("I01", "I06", "I10", "I27", "I35", "I37", "I39", "I41", "I43", "I48")      # #5's manifest flags, checked by a test
WAN = ("I35", "I37", "I48")
PILOT_OPTIONS = (Option.T, Option.T_UNPAGINATED, Option.D, Option.M)
LAYOUTS = (Layout.S1, Layout.S2)
BASELINE_INSTANCES = WAN            # 1 event-free, 2 event-bearing; science's step A runs on 3 instances
BLOCK_CELLS = {1: tuple((o, Layout.S1) for o in PILOT_OPTIONS),                    # T, T-unpaginated, D, M in S1
               2: tuple((o, Layout.S2) for o in (Option.T, Option.D, Option.M))}   # T, D, M in S2 (science's amendment)
MAX_LEVEL = 16                      # science's levels include 12 and 16; above that needs an explicit decision
M_MOUNTS_PROVEN = 16                # oneclient mounts site_g was shown to hold at once (science's ruling): M's cap; a later proof of more raises it
M_LOAD_SHARE = 0.875                # the share of M's cap the curve's mean M load stays near (science, #34, 2 Nov 17:22Z: 14 of 16)
DUTY_MAX_LEVEL = int(3 * M_MOUNTS_PROVEN * M_LOAD_SHARE)   # 42: the curve's hard limit above MAX_LEVEL (science, #34, 17:22Z, replacing 48); above it
                                                           # needs a later ruling, named decision or not; it moves with M_MOUNTS_PROVEN, never by hand


def pilot_plan(seed: int, instances=PILOT, options=PILOT_OPTIONS, layouts=LAYOUTS, tag: str = "pilot",
               reps: int = 1) -> list[Plan]:
    """Single runs, one per instance x option x layout x repetition, in a seeded order. One repetition keeps the bare tag."""
    tags = [tag] if reps == 1 else [f"{tag}-r{r}" for r in range(1, reps + 1)]
    runs = [Plan(i, o, la, tag=t) for t in tags for i in instances for o in options for la in layouts]
    order = np.random.default_rng(seed).permutation(len(runs))
    return [runs[int(k)] for k in order]


def baseline_plan(seed: int, instances=BASELINE_INSTANCES, k: int = 3, untraced_k: int = 1, controls: bool = False) -> list[tuple[Plan, str]]:
    """Science's step A (17:49Z): 24 traced, enforced runs (T, T-unpaginated, D, M x S1, S2 x the 3 instances) and `untraced_k`
    untraced ones per cell for the tracer's ratio. The overhead controls (`controls=True`) moved into the campaign, where the
    same function gives the interleaved pairs: (plan, arm), alternating per instance and cell, never a block.

    Per cell, `k` picks that cycle the instances (so every instance is run in every cell, and with k = 5 the cell has
    k >= 5 per arm, the analysis's min_k). Each pick holds the arms side by side in time, in an order that rotates with the
    pick: `enforced` (traced, what A requires exact) and `control` (traced, no enforcement; T-unpaginated has none, without
    the gate it is T), plus `untraced` (enforced, for the traced-vs-untraced table) on the first `untraced_k` picks.
    The picks are then shuffled, so that load drift hits all the arms alike."""
    picks = []
    cells = [(o, la) for o in PILOT_OPTIONS for la in LAYOUTS]
    for o, la in cells:
        for j in range(k):
            arms = ["enforced"] + (["control"] if controls and o != Option.T_UNPAGINATED else []) + (["untraced"] if j < untraced_k else [])
            arms = arms[j % len(arms):] + arms[:j % len(arms)]
            i = instances[j % len(instances)]
            picks.append([(Plan(i, o, la, tag=f"base-{arm[:3]}-p{j}"), arm) for arm in arms])
    order = np.random.default_rng(seed).permutation(len(picks))
    return [row for q in order for row in picks[int(q)]]


PROBE_SHAPES = {"T": Option.T, "M": Option.M}      # the live check's shapes (amendment 25(e)): T's S1 cell and M's S1 cell


def parse_probe_files(text: str) -> dict[str, int]:
    """"T=146,M=240" -> {"T": 146, "M": 240}: the file count of each shape's prefix cell (a probe's baseline), whole numbers of at least 1, each shape at most once."""
    got: dict[str, int] = {}
    for part in (x for x in text.split(",") if x):
        shape, sep, n = part.partition("=")
        if not sep or shape not in PROBE_SHAPES or shape in got or not n.isdigit() or int(n) < 1:
            raise ValueError(f"probe files {part!r}: write SHAPE=N for each of {sorted(PROBE_SHAPES)} once, N a whole number of at least 1")
        got[shape] = int(n)
    if not got:
        raise ValueError(f"probe files {text!r}: write SHAPE=N for each of {sorted(PROBE_SHAPES)}")
    return got


def probe_shape(option: Option) -> str:
    """The live check's shape name of an option (T or M); the prefix cell is run for these two only."""
    for shape, o in PROBE_SHAPES.items():
        if o == option:
            return shape
    raise ValueError(f"option {option}: the live check's shapes are {sorted(PROBE_SHAPES)}")


def probe_baseline_plan(seed: int, files: dict[str, int], instances=BASELINE_INSTANCES, k: int = 3, untraced_k: int = 0) -> list[tuple[Plan, str]]:
    """The baseline's extra cell for the live probe (amendment 25(e)): per shape in `files`, `k` single S1 runs that each read that shape's `files` first files (`runner.probe_days`),
    cycling the instances, enforced and traced (`untraced_k` of the picks also untraced, for a probe run with `--untraced`). They are run by `baseline --probe-files`, ALONE and into a
    directory of their own: the ordinary baseline's plan (`baseline_plan`) is not touched. The tag carries the count, so no key is a whole-cell baseline's."""
    picks = []
    for shape in sorted(files):
        o, n = PROBE_SHAPES[shape], files[shape]
        for j in range(k):
            arms = ["enforced"] + (["untraced"] if j < untraced_k else [])
            arms = arms[j % len(arms):] + arms[:j % len(arms)]
            picks.append([(Plan(instances[j % len(instances)], o, Layout.S1, tag=f"base-pf{n}-{arm[:3]}-p{j}"), arm) for arm in arms])
    order = np.random.default_rng(seed).permutation(len(picks))
    return [row for q in order for row in picks[int(q)]]


def mix_slots(seed: int, block: int, level: int, rep: int = 1, instances=BASELINE_INSTANCES, max_level: int = MAX_LEVEL) -> list[list[Plan]]:
    """One list of runs per sandbox slot: the block's cells in a random order of the slot's own, each on an instance that
    has a baseline. At any moment `level` sandboxes are up, mixing the block's cells (science's amendment). `max_level` above
    `MAX_LEVEL` only for the duty-cycle curve, with the decision that allows it (`curve --above-16-decision`)."""
    if block not in BLOCK_CELLS:
        raise ValueError(f"block {block}: the blocks are {sorted(BLOCK_CELLS)}")
    if not 1 <= level <= max_level or max_level > DUTY_MAX_LEVEL:
        raise ValueError(f"level {level}: above {MAX_LEVEL} needs an explicit decision")
    rng = np.random.default_rng([seed, block, level, rep])
    cells = BLOCK_CELLS[block]
    slots = []
    for s_ in range(level):
        order = rng.permutation(len(cells))
        slots.append([Plan(instances[(s_ + n) % len(instances)], cells[int(c)][0], cells[int(c)][1],
                           tag=f"mix-b{block}-c{level}-r{rep}-s{s_}-n{n}") for n, c in enumerate(order)])
    return slots


DUTY_MEASURED_CYCLES = 1             # amendment 34(a), as 33(c) registered (science, #34, 13:15Z; it was 2 from #34, 18:53Z): a duty-cycle level is one warm-up cycle and max(1, ceil(3k / c)) measured cycles
DUTY_MIN_READS = 3                   # ... with at least this many measured reads per cell, else the measured cycles are extended
DUTY_MIN_LEVEL = 2                   # the duty-cycle ladder starts at 2: the baselines are level 1


def duty_cycles(level: int, n_cells: int) -> int:
    """The measured cycles of a duty-cycle level (one run per slot per cycle): max(1, ceil(3k / c)), amendment 34(a) (33(c) as registered): one cycle where it gives 3 reads per
    cell (c >= 3k), else as many as it takes. It was two cycles at least (18:53Z, 2 Nov), so a level from 12 up ran two."""
    if level < 1 or n_cells < 1:
        raise ValueError(f"level {level}, cells {n_cells}")
    return max(DUTY_MEASURED_CYCLES, -(-DUTY_MIN_READS * n_cells // level))


def duty_slots(seed: int, block: int, level: int, rep: int = 1, instances=BASELINE_INSTANCES) -> list[list[Plan]]:
    """The duty-cycle level's counted runs: `duty_cycles` = max(1, ceil(3k / c)) runs per slot (amendment 34(a)). The run t = j * level + s (cycle j, slot s) takes the cell
    `order[t mod k]` of one seeded order, so the cells are spread evenly over the slots and the cycles and, with consecutive t, every cell gets
    at least floor(level * cycles / k) >= 3 reads. When k divides the level every cycle would hand a slot the same cell, so the cells shift by
    the cycle."""
    if block not in BLOCK_CELLS:
        raise ValueError(f"block {block}: the blocks are {sorted(BLOCK_CELLS)}")
    if not DUTY_MIN_LEVEL <= level <= DUTY_MAX_LEVEL:
        raise ValueError(f"level {level}: the duty-cycle ladder is {DUTY_MIN_LEVEL}..{DUTY_MAX_LEVEL}")
    cells = BLOCK_CELLS[block]
    k = len(cells)
    order = [int(c) for c in np.random.default_rng([seed, block, level, rep, 0xD07]).permutation(k)]
    shift = 1 if level % k == 0 else 0
    return [[Plan(instances[(s_ + j) % len(instances)], cells[order[(j * level + s_ + j * shift) % k]][0], cells[order[(j * level + s_ + j * shift) % k]][1],
                  tag=f"mix-b{block}-c{level}-r{rep}-s{s_}-n{j}") for j in range(duty_cycles(level, k))] for s_ in range(level)]


def padding_plan(rng: np.random.Generator, block: int, level: int, rep: int, slot: int, n: int, instances=BASELINE_INSTANCES) -> Plan:
    """A run that only keeps the level full until every slot's counted runs are done; it enters no statistic."""
    o, la = BLOCK_CELLS[block][int(rng.integers(len(BLOCK_CELLS[block])))]
    return Plan(instances[(slot + n) % len(instances)], o, la, tag=f"mixpad-b{block}-c{level}-r{rep}-s{slot}-n{n}")


def disk_needed_gib(block: int, level: int, s2_bytes: int) -> float:
    """/mnt/volume2 space a level can take at worst, on top of the margin: in block 2 every slot may be in D at once, holding
    the file twice (spool and /work); in block 1, D's daily files are spooled one at a time."""
    return level * (2 * s2_bytes / 1024 ** 3 if block == 2 else 1.0)


def parse_instances(text: str, allowed=PILOT) -> tuple[str, ...]:
    """"I35,I37" -> those instances, refusing any outside the pilot set (their extent has no frozen timing role)."""
    chosen = tuple(x for x in text.split(",") if x)
    wrong = [x for x in chosen if x not in allowed]
    if wrong or not chosen:
        raise ValueError(f"instances {wrong or text!r}: choose among {allowed}")
    return chosen
