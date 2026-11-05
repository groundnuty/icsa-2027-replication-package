"""Reference marine-heatwave detector (issue #4); API in refdet-api.md.

Three modes share `detect`: (a) published fields, (b) computed fields, (c) a region and
one target period. Domain mode is the whole grid over `grid.DETECTION_WINDOW`.

Additions to the agreed API (all optional): `detect(..., window=, precision=)` clips the day
axis and picks the comparison precision, `domain_window()` and `baseline_days()` give the
published windows as day indices, `computed_fields(..., baseline=, estimator=, precision=)`.
Computed fields are float64 (the reference computes in float64 throughout); published fields
are float32 as published. `precision="octave"` is a validation-only emulation of the authors'
code under Octave (see core).
"""
from __future__ import annotations

import dataclasses

import numpy as np

from .. import grid
from ..extent import CellBox
from . import core
from .data import load_sst, published_arrays, sea_mask

__all__ = ["Fields", "Event", "Detection", "published_fields", "computed_fields", "sea_mask", "sea_cells",
           "detect", "load_sst", "domain_window", "baseline_days"]


@dataclasses.dataclass(frozen=True)
class Fields:
    """Threshold and climatology by day of year (366-day calendar)."""
    m90: np.ndarray    # (366, h, w), index 0 = 1 Jan, 59 = 29 Feb; float64 computed, float32 published
    mclim: np.ndarray  # (366, h, w)


@dataclasses.dataclass(frozen=True)
class Event:
    onset: int  # global day index, inclusive
    end: int    # global day index, inclusive


@dataclasses.dataclass(frozen=True)
class Detection:
    days: np.ndarray       # int64 (n,), the contiguous day axis the detection ran on
    cell_mask: np.ndarray  # bool (n, h, w): per-cell MHW state after the duration and gap rules
    active: np.ndarray     # bool (n,): any sea cell in a per-cell event with a finite anomaly
    events: list[Event]    # maximal runs of active days


def sea_cells(*sst_parts: np.ndarray) -> np.ndarray:
    """The prompt's sea-cell rule, used by the reference in computed and regional modes (science,
    protocol a5e4400): a cell is sea iff its SST is finite on every day of every part given, i.e. the
    required baseline extent 1991-12-27..2003-01-05 and the target period. The bathymetry mask
    (`sea_mask`, = finite BALarea) is used only for the Octave equivalence and Step B, as the authors did."""
    if not sst_parts:
        raise ValueError("no SST given")
    out = None
    for a in sst_parts:
        f = np.isfinite(np.asarray(a)).all(axis=0)
        out = f if out is None else out & f
    return out


def required_baseline_days() -> np.ndarray:
    """The baseline days detectc reads: 1991-12-27..2003-01-05 (baseline +- the 5-day half window)."""
    b0, b1 = baseline_days()
    return np.arange(b0 - core.HALF_WINDOW, b1 + core.HALF_WINDOW + 1, dtype=np.int64)


def baseline_days() -> tuple[int, int]:
    return grid.day_index(grid.BASELINE[0]), grid.day_index(grid.BASELINE[1])


def domain_window() -> tuple[int, int]:
    return grid.day_index(grid.DETECTION_WINDOW[0]), grid.day_index(grid.DETECTION_WINDOW[1])


def published_fields(box: CellBox) -> Fields:
    m90, mclim = published_arrays(box)
    return Fields(m90, mclim)


def computed_fields(sst: np.ndarray, days: np.ndarray, box: CellBox, *,
                    baseline: tuple[int, int] | None = None,
                    estimator: tuple[float, float] | str | None = None,
                    precision: str = "float64") -> Fields:
    """Mode (b): thresholds and climatology from whichever days are given (days outside
    the baseline +- 5 are ignored, missing days are absent). Float64."""
    sst = np.asarray(sst)
    if sst.shape != (len(days), *box.shape):
        raise ValueError(f"sst shape {sst.shape} != {(len(days), *box.shape)}")
    m90, mclim = core.climatology(sst, days, baseline=baseline or baseline_days(), estimator=estimator,
                                  precision=precision)
    return Fields(m90, mclim)


def _events_from_active(days: np.ndarray, active: np.ndarray) -> list[Event]:
    a = np.concatenate([[False], active, [False]]).astype(np.int8)
    d = np.diff(a)
    starts = np.nonzero(d == 1)[0]
    ends = np.nonzero(d == -1)[0] - 1
    return [Event(int(days[s]), int(days[e])) for s, e in zip(starts, ends)]


_BAND_BYTES = 1 << 30


def detect(sst: np.ndarray, days: np.ndarray, box: CellBox, fields: Fields,
           sea: np.ndarray | None = None, *, window: tuple[int, int] | None = None,
           precision: str = "float64") -> Detection:
    """Per-cell detection on `sst` (len(days), h, w), then the domain/region event rule.

    The day axis is made contiguous over [min(days), max(days)] (or `window`); days not
    in `days`, and NaN values, are no data. With `window` the axis is exactly that range.
    """
    days = np.asarray(days, dtype=np.int64)
    sst = np.asarray(sst)
    h, w = box.shape
    if sst.shape != (days.size, h, w):
        raise ValueError(f"sst shape {sst.shape} != {(days.size, h, w)}")
    if fields.m90.shape != (366, h, w):
        raise ValueError(f"fields shape {fields.m90.shape} != {(366, h, w)}")
    if days.size == 0:
        raise ValueError("no days")
    lo, hi = (int(days.min()), int(days.max())) if window is None else window
    axis = np.arange(lo, hi + 1, dtype=np.int64)
    if window is not None or not np.array_equal(axis, days):
        x = np.full((axis.size, h, w), np.nan, np.result_type(sst.dtype, np.float32))  # input precision kept
        inside = (days >= lo) & (days <= hi)
        x[days[inside] - lo] = sst[inside]
    else:
        x = sst
    if sea is None:
        raise ValueError("pass sea: sea_cells(baseline sst, target sst) for computed/regional modes, "
                         "or sea_mask(box) (the authors' bathymetry mask) for the Octave equivalence and Step B")
    sea = np.asarray(sea, bool)
    doy = core.doy366(axis)
    n = axis.size
    cell = np.zeros((n, h, w), bool)
    active = np.zeros(n, bool)
    rows = max(1, int(_BAND_BYTES // (n * w * 24)))  # float64 sst + threshold per band, plus masks
    for r0 in range(0, h, rows):
        r1 = min(h, r0 + rows)
        xb = x[:, r0:r1]
        cm = core.cell_events(xb, fields.m90[:, r0:r1], doy, precision=precision)
        cm &= sea[r0:r1]
        cell[:, r0:r1] = cm
        # Step_3 takes the nanmean of the anomaly (sst - mclim): a day is active only if an event cell has one
        fin = np.isfinite(xb) & np.isfinite(fields.mclim[:, r0:r1][doy])
        active |= (cm & fin).any(axis=(1, 2))
    return Detection(axis, cell, active, _events_from_active(axis, active))


from .truth import ground_truth  # noqa: E402  (needs the names above)

__all__ += ["ground_truth", "required_baseline_days"]
