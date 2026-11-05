"""The calibration matrix: which scripted runs to do per option x layout (x condition).

At least 60 faulted and 30 fault-free runs per option x layout, as issue #11 requires: each
applicable fault type gets ceil(min_faulted / n_types) replicates (so the faulted count is >= 60),
and the controls are replicates of Fault.NONE. Fault parameters are paired across options and
layouts (see scenarios.py). Faulted and control runs are interleaved in one seeded random order,
recorded as `order`. Pooled recall mixes fault types, so reports give it per fault type too.
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np

from icsa.records import Layout, Option

from .observability import LAYOUTS, OPTIONS, RECORDS_OF, Obs, applicable_faults, assert_ready_for_calibration, classify
from .scenarios import Condition, Fault, Scenario, make_scenario


@dataclasses.dataclass(frozen=True)
class PlannedRun:
    order: int
    scenario: Scenario
    masking: object | None = None      # masking.Masking of the run, sealed before any run (seal_masking)


def per_instance(s: Scenario) -> bool:
    """Does any of the option's records class this scenario's cell observable_per_instance?"""
    return any(classify(s.fault, s.layout, s.option, rec, s.condition).obs is Obs.PER_INSTANCE for rec in RECORDS_OF[s.option])


def seal_masking(plan: list[PlannedRun], required, manifests: dict) -> list[PlannedRun]:
    """The masking verdict of EVERY run (masking.py; every option has a byte-level record), from the scenario, the
    calibration instance's required set and the static manifests only: computed BEFORE any run and carried into the
    claimed plan's sha. In an observable_per_instance cell it decides the run's class; in every byte-level cell it
    gives the two masked shares reported beside recall (runs fully masked, omitted days served anyway)."""
    from .masking import masking
    out = []
    for r in plan:
        man = manifests.get(r.scenario.layout)
        if man is None:
            raise ValueError(f"no {r.scenario.layout.value} manifest for the masking verdict of {r.scenario.sid}")
        out.append(dataclasses.replace(r, masking=masking(r.scenario, required, man)))
    return out


def build_matrix(master_seed: int, options=OPTIONS, layouts=LAYOUTS, min_faulted: int = 60,
                 n_controls: int = 30) -> list[PlannedRun]:
    """The public entry: refuses unless every cell is classed, from the COMMITTED LIVE_CLASSES.json."""
    assert_ready_for_calibration()
    return _build_matrix(master_seed, options, layouts, min_faulted, n_controls)


def _build_matrix(master_seed: int, options=OPTIONS, layouts=LAYOUTS, min_faulted: int = 60,
                  n_controls: int = 30) -> list[PlannedRun]:
    """Matrix construction without the readiness gate: for tests of sizes and ordering only."""
    runs: list[Scenario] = []
    for opt in options:
        conds = list(Condition) if opt is Option.M else [Condition.COLD]
        for layout in layouts:
            faults = applicable_faults(layout, opt)
            n_each = math.ceil(min_faulted / len(faults))
            for cond in conds:
                for f in faults:
                    runs += [make_scenario(f, layout, opt, cond, r, master_seed) for r in range(n_each)]
                runs += [make_scenario(Fault.NONE, layout, opt, cond, r, master_seed) for r in range(n_controls)]
    rng = np.random.default_rng([master_seed, 7919])
    perm = rng.permutation(len(runs))
    return [PlannedRun(i, runs[j]) for i, j in enumerate(perm)]


def calibration_plan(master_seed: int, ledger_path, options=OPTIONS, layouts=LAYOUTS, min_faulted: int = 60,
                     n_controls: int = 30, *, required, manifests: dict):
    """The one entry for the real calibration: readiness gate (every cell classed from the committed live
    file), build, seal the per-run masking verdicts (`required`: the calibration instance's required set;
    `manifests`: {Layout: Manifest}), and claim in the ledger (refused if the ledger already holds a matrix).
    Returns (plan, claim)."""
    from .ledger import Ledger
    plan = seal_masking(build_matrix(master_seed, options, layouts, min_faulted, n_controls), required, manifests)
    claim = Ledger(ledger_path).claim(plan, (master_seed, tuple(o.value for o in options),
                                             tuple(l.value for l in layouts), min_faulted, n_controls))
    return plan, claim
