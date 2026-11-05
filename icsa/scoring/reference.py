"""Per-instance references and the counterfactual (cached across the runs of an instance).

Detections on the instance's target period, all through #4's `icsa.refdet`:
  gt         the ground truth for event F1 and mask agreement: computed mode on the full
             required extent (reference rule, protocol/parameters.md; #4). It is the same
             detection as `full`;
  full       computed mode on the full required extent;
  cf         computed mode on the run's analysed extent (#9): percentiles from the
             baseline days available, units not analysed are NaN = no data;
  published  published-field mode, kept only for the mode-agreement report (validation,
             not scoring).
Sea cells follow the prompt's rule (`refdet.sea_cells`): finite on every day of the required
baseline extent (1991-12-27..2003-01-05, from #5) and of the target period.
computation discrepancy = agent vs cf; omission discrepancy = cf vs full
(both computed mode, so the decomposition is internally consistent).
The reference detector module is injected (`refdet`), so tests use a stub.
"""
from __future__ import annotations

import dataclasses
from types import ModuleType
from typing import Any, Callable

import numpy as np

from .. import grid
from ..extent import CellBox, Extent, PartedExtent
from ..records import Instance
from . import events, masks


@dataclasses.dataclass(frozen=True)
class Reference:
    instance: Instance
    box: CellBox
    required: PartedExtent
    target_days: np.ndarray        # int64 global day indices of the target period
    sea: np.ndarray                # bool (h, w)
    sst_baseline: np.ndarray       # float32 (n_baseline_days, h, w), over required.baseline.days
    sst_target: np.ndarray         # float32 (n_target_days, h, w)
    gt: Any                        # refdet.Detection, the ground truth: computed mode, full required extent
    full: Any                      # refdet.Detection, computed from the full required extent (= gt)
    refdet: Any                    # the module that built it, reused for the counterfactual
    published: Any = None          # refdet.Detection with the published fields (mode-agreement report only)


def target_days_of(instance: Instance) -> np.ndarray:
    a, b = grid.day_index(instance.target.start), grid.day_index(instance.target.end)
    return np.arange(a, b + 1, dtype=np.int64)


def build_reference(instance: Instance, required: PartedExtent, refdet: ModuleType,
                    sst_loader: Callable[[CellBox, np.ndarray], np.ndarray] | None = None) -> Reference:
    box = CellBox(instance.lat0, instance.lat1, instance.lon0, instance.lon1)
    tdays = target_days_of(instance)
    if not np.array_equal(required.target.days, tdays):
        raise ValueError("required target extent days differ from the instance's target period")
    load = sst_loader or refdet.load_sst
    sst_b = load(box, required.baseline.days)
    sst_t = load(box, tdays)
    sea = refdet.sea_cells(sst_b, sst_t)
    full = _computed_detection(refdet, box, sea, tdays, required, sst_b, sst_t,
                               required.baseline.mask, required.target.mask)
    published = refdet.detect(sst_t, tdays, box, refdet.published_fields(box), sea)
    return Reference(instance, box, required, tdays, sea, sst_b, sst_t, full, full, refdet, published)


def _kept(required_part: Extent, analysed_part: Extent) -> np.ndarray:
    """bool (required days, h, w): the units of `required_part` that were analysed."""
    common = analysed_part.intersection(required_part)
    out = np.zeros((required_part.days.size, *required_part.box.shape), bool)
    out[np.searchsorted(required_part.days, common.days)] = common.mask
    return out


def _computed_detection(refdet, box, sea, tdays, required: PartedExtent, sst_b, sst_t,
                        keep_b: np.ndarray, keep_t: np.ndarray):
    """Computed-mode detection using only the units in keep_b / keep_t (bool, the
    shapes of sst_b / sst_t); the rest is NaN = no data, baseline days with no
    kept unit are absent. Shared by the full-data reference (keep = required)
    and the counterfactual (keep = analysed within required)."""
    sb = np.where(keep_b, sst_b, np.nan).astype(np.float32)
    have = keep_b.any(axis=(1, 2))
    fields = refdet.computed_fields(sb[have], required.baseline.days[have], box)
    st = np.where(keep_t, sst_t, np.nan).astype(np.float32)
    return refdet.detect(st, tdays, box, fields, sea)


def counterfactual(ref: Reference, analysed: PartedExtent):
    """Computed-mode detection on exactly the data the agent analysed (within the required extent)."""
    rb, rt = ref.required.baseline, ref.required.target
    return _computed_detection(ref.refdet, ref.box, ref.sea, ref.target_days, ref.required,
                               ref.sst_baseline, ref.sst_target,
                               _kept(rb, analysed.baseline), _kept(rt, analysed.target))


def detection_events(det, days: np.ndarray) -> list[np.ndarray]:
    """Unit arrays of a Detection's events (per-cell state within each event's days)."""
    out = []
    for e in det.events:
        i0, i1 = events.span(days, e.onset, e.end)
        out.append(events.event_units(det.cell_mask, i0, i1))
    return out


def _mode_counts(gt, full, sea) -> tuple[int, int, int, int, int, int]:
    """(event tp, n computed events, n published events, cell-day tp, n computed, n published)."""
    m = events.match_events(detection_events(full, full.days), detection_events(gt, gt.days))
    a, r = full.cell_mask & sea, gt.cell_mask & sea
    return m.tp, m.n_agent, m.n_ref, int((a & r).sum()), int(a.sum()), int(r.sum())


def _f1s(c) -> dict[str, float | None]:
    tp_e, n_a, n_r, tp_c, n_ca, n_cr = c
    return {"event_f1": 2 * tp_e / (n_a + n_r) if n_r else None,
            "cell_day_f1": 2 * tp_c / (n_ca + n_cr) if n_cr else None}


def mode_agreement_per_instance(pairs: list[tuple[Any, Any]], sea_masks: list[np.ndarray]) -> list[dict]:
    """Agreement between published-field and computed modes for each instance:
    `pairs` are (published, full) Detections (`Reference.published`, `Reference.full`),
    `sea_masks` their sea masks."""
    return [_f1s(_mode_counts(gt, full, sea)) for (gt, full), sea in zip(pairs, sea_masks)]


def mode_agreement(pairs: list[tuple[Any, Any]], sea_masks: list[np.ndarray]) -> dict[str, float | None]:
    """The same, pooled once over all instances (event counts and cell-day counts summed)."""
    if not pairs:
        return {"event_f1": None, "cell_day_f1": None}
    tot = np.sum([_mode_counts(gt, full, sea) for (gt, full), sea in zip(pairs, sea_masks)], axis=0)
    return _f1s(tuple(int(x) for x in tot))
