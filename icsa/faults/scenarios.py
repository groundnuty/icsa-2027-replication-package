"""The fault catalogue: scripted runs with a KNOWN injected omission.

FORBIDDEN (issue #11): defining an injected omission from any record or instrument output. Here it
is a pure function of the scenario parameters and the required set. This module imports no parser,
detector or record module (a test enforces it).

Terms, per required day (the unit, in both layouts):
- unread:      the script never touches the day's data (file skipped / chunk skipped).
- header_only: the script reads the file's header (bytes below the first data byte) but not the data.
- unused:      the data is read in full but the analysis leaves it out ("full read, partial use",
               "wrong region"). By design no platform record can show it.
A day is OMITTED if it is in any of the three. The detector can only ever flag unread days; what it
can see of the others is the observability table's business.

Pairing: fault parameters depend on (master seed, fault type, replicate index) and NOT on option,
layout or condition, so every option x layout is calibrated against the same draws.
"""
from __future__ import annotations

import dataclasses
import enum
import math
from typing import Iterable

import numpy as np

from icsa import grid
from icsa.records import Layout, Option

from .units import Required


class Fault(str, enum.Enum):
    NONE = "none"                          # fault-free control
    WHOLE_FILE_SKIP = "whole_file_skip"    # S1: random required files never read
    FILE_RANGE_SKIP = "file_range_skip"    # S1: a contiguous run of required files never read
    CHUNK_SKIP = "chunk_skip"              # S2: random required time steps never read
    CHUNK_RANGE_SKIP = "chunk_range_skip"  # S2: a contiguous run of required time steps never read
    BASELINE_DROPPED = "baseline_dropped"  # all baseline days never read
    TARGET_DROPPED = "target_dropped"      # all target days never read
    WRONG_PERIOD = "wrong_period"          # the target days replaced by the same days one year earlier/later
    HEADER_ONLY = "header_only"            # a share of the required days: header read, data not
    FULL_READ_PARTIAL_USE = "full_read_partial_use"  # all read; a share of days left out of the analysis
    WRONG_REGION = "wrong_region"          # all read; the analysed box misses the required one
    LISTING_TRUNCATION = "listing_truncation"  # S1: only the first `page_size` names ever listed


class Condition(str, enum.Enum):
    COLD = "cold"                  # empty client buffer, default read-ahead
    WARM_BUFFER = "warm_buffer"    # M: the days to be read are read once before the run
    PREFETCH_ON = "prefetch_on"    # M: oneclient prefetch enabled


class Mode(str, enum.Enum):
    FULL = "full"
    HEADER = "header"


FRACTIONS = (0.02, 0.05, 0.10, 0.25, 0.50)   # stratified over replicates, fixed in advance
HEADER_FRACTIONS = (0.10, 0.25, 0.50, 1.00)
PAGE_SIZE = 1000                             # the official client's default and only page (#10 Q3)
SHIFT_DAYS = (365, -365)

_FAULT_ORDER = [f.value for f in Fault]


@dataclasses.dataclass(frozen=True)
class Scenario:
    fault: Fault
    layout: Layout
    option: Option
    condition: Condition
    replicate: int           # index within (fault): the pairing key
    master_seed: int
    params: tuple            # sorted ((name, value), ...): frozen hashable; see `draw_params`

    def p(self, name: str):
        return dict(self.params)[name]

    @property
    def sid(self) -> str:
        return f"{self.fault.value}.{self.layout.value}.{self.option.value}.{self.condition.value}.r{self.replicate}"


def draw_params(fault: Fault, replicate: int, master_seed: int) -> tuple:
    """Fault parameters: a function of (seed, fault, replicate) only."""
    rng = np.random.default_rng([master_seed, _FAULT_ORDER.index(fault.value), replicate])
    d: dict = {}
    if fault in (Fault.WHOLE_FILE_SKIP, Fault.CHUNK_SKIP, Fault.FILE_RANGE_SKIP, Fault.CHUNK_RANGE_SKIP,
                 Fault.FULL_READ_PARTIAL_USE):
        d["fraction"] = FRACTIONS[replicate % len(FRACTIONS)]
        d["u"] = float(rng.random())          # placement in [0,1): start of a range / shuffle seed
        d["pick_seed"] = int(rng.integers(0, 2**31 - 1))
    elif fault is Fault.HEADER_ONLY:
        d["fraction"] = HEADER_FRACTIONS[replicate % len(HEADER_FRACTIONS)]
        d["pick_seed"] = int(rng.integers(0, 2**31 - 1))
    elif fault is Fault.WRONG_PERIOD:
        d["shift"] = SHIFT_DAYS[replicate % len(SHIFT_DAYS)]
    elif fault is Fault.LISTING_TRUNCATION:
        d["page_size"] = PAGE_SIZE
    return tuple(sorted(d.items()))


def make_scenario(fault: Fault, layout: Layout, option: Option, condition: Condition,
                  replicate: int, master_seed: int) -> Scenario:
    return Scenario(fault, layout, option, condition, replicate, master_seed,
                    draw_params(fault, replicate, master_seed))


@dataclasses.dataclass(frozen=True)
class Injection:
    unread: frozenset[int]
    header_only: frozenset[int]
    unused: frozenset[int]
    extra_read: frozenset[int]        # non-required days the script also reads (wrong period)

    @property
    def omitted(self) -> frozenset[int]:
        return self.unread | self.header_only | self.unused


@dataclasses.dataclass(frozen=True)
class ReadPlan:
    """What the scripted run does, per day. Days absent here are not touched at all."""
    touch: dict[int, Mode]
    analysed: frozenset[int]          # days the analysis uses (differs from touched for 'unused')


def _pick(days: tuple[int, ...], k: int, seed: int) -> frozenset[int]:
    k = min(k, len(days))
    rng = np.random.default_rng(seed)
    return frozenset(int(x) for x in rng.choice(np.array(days), size=k, replace=False))


def _range(days: tuple[int, ...], k: int, u: float) -> frozenset[int]:
    """k consecutive entries of the sorted required days, starting at position floor(u*(n-k+1))."""
    k = min(k, len(days))
    start = min(int(u * (len(days) - k + 1)), len(days) - k)
    return frozenset(days[start:start + k])


def _k(fraction: float, n: int) -> int:
    return max(1, math.ceil(fraction * n))


def injection(s: Scenario, req: Required) -> Injection:
    days = req.days
    none = frozenset()
    f = s.fault
    if f is Fault.NONE:
        return Injection(none, none, none, none)
    if f in (Fault.WHOLE_FILE_SKIP, Fault.CHUNK_SKIP):
        return Injection(_pick(days, _k(s.p("fraction"), len(days)), s.p("pick_seed")), none, none, none)
    if f in (Fault.FILE_RANGE_SKIP, Fault.CHUNK_RANGE_SKIP):
        return Injection(_range(days, _k(s.p("fraction"), len(days)), s.p("u")), none, none, none)
    if f is Fault.BASELINE_DROPPED:
        return Injection(frozenset(req.baseline), none, none, none)
    if f is Fault.TARGET_DROPPED:
        return Injection(frozenset(req.target), none, none, none)
    if f is Fault.WRONG_PERIOD:
        shifted = frozenset(d + s.p("shift") for d in req.target if 0 <= d + s.p("shift") < grid.NDAYS)
        req_all = set(days)
        # the target days are not read; the shifted days are, and count only where they are required
        return Injection(frozenset(req.target) - shifted, none, none, shifted - req_all)
    if f is Fault.HEADER_ONLY:
        return Injection(none, _pick(days, _k(s.p("fraction"), len(days)), s.p("pick_seed")), none, none)
    if f is Fault.FULL_READ_PARTIAL_USE:
        return Injection(none, none, _pick(days, _k(s.p("fraction"), len(days)), s.p("pick_seed")), none)
    if f is Fault.WRONG_REGION:
        return Injection(none, none, frozenset(days), none)
    if f is Fault.LISTING_TRUNCATION:
        # names sort in day order (sst_YYYYMMDD), so the first page holds days 0..page_size-1
        return Injection(frozenset(d for d in days if d >= s.p("page_size")), none, none, none)
    raise ValueError(f)


def read_plan(s: Scenario, req: Required) -> ReadPlan:
    """The script. Derived from the same injection, so plan and injected set cannot drift apart."""
    inj = injection(s, req)
    touch: dict[int, Mode] = {}
    for d in req.days:
        if d not in inj.unread:
            touch[d] = Mode.HEADER if d in inj.header_only else Mode.FULL
    for d in inj.extra_read:
        touch[d] = Mode.FULL
    if s.fault is Fault.WRONG_PERIOD:
        shifted = {d + s.p("shift") for d in req.target}
        for d in shifted:
            if 0 <= d < grid.NDAYS:
                touch.setdefault(d, Mode.FULL)
    analysed = frozenset(d for d in req.days if d not in inj.omitted)
    return ReadPlan(touch, analysed)
