"""Per-cell Hobday detection exactly as m_mhw `detectc` runs it in the authors'
Step_2 (Bashiri et al. 2025), vectorised over cells with numpy.

Port notes (the MATLAB code, not the prose, is the spec):
* Climatology/threshold for day-of-year i (366-day calendar, 29 Feb = 60) pool,
  per baseline day with that day-of-year, the +-5 calendar days around it,
  taken from the data padded by 5 days each side of the baseline. A day that
  falls in several windows is counted once (`any(...)` in detectc), and padding
  days are never window centres.
* The 29 Feb entry is skipped in the loop and set to the NaN-ignoring mean of
  entries 59 and 61 *before* smoothing.
* Both fields are smoothed with a circular 31-day moving mean (NaN ignored).
* Exceedance is `sst >= threshold`; NaN never exceeds.
* Precision: float64 throughout by default (percentiles, means, smoothing and the comparison).
  `precision="octave"` instead emulates what the authors' chain does under GNU Octave 9.2 on
  single SST (tools/octave/t_semantics.m): per-day-of-year quantile in single arithmetic
  ((1-r)*x_i + r*x_{i+1}, Octave's method 5), mean as single(double sum / n), day 60,
  smoothing in double, and the comparison single(sst) >= single(m90). It exists only to show
  that the residual against Octave is arithmetic precision; MATLAB's own rules are unverified.
* Runs shorter than `min_duration` are dropped first, then runs separated by
  gaps <= `max_gap` days are joined (transitively).
"""
from __future__ import annotations

import datetime as dt

import numpy as np

from .. import grid

HALF_WINDOW = 5
SMOOTH_WIDTH = 31
MIN_DURATION = 5
MAX_GAP = 2
PERCENTILE = 0.9
PRECISIONS = ("float64", "octave")

# A leap year fixes the 366-entry day-of-year calendar used by detectc.
_LEAP_CUM = np.concatenate([[0], np.cumsum([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])])


def doy366(days: np.ndarray) -> np.ndarray:
    """0-based day of year on the 366-day calendar (index 59 = 29 Feb) for day indices."""
    days = np.asarray(days, dtype=np.int64)
    d64 = np.datetime64(grid.DAY0, "D") + days.astype("timedelta64[D]")
    months = d64.astype("datetime64[M]")
    month0 = (months.astype(np.int64) % 12)
    dom = (d64 - months.astype("datetime64[D]")).astype(np.int64)
    return _LEAP_CUM[month0] + dom


def quantile_matlab(x: np.ndarray, p: float, axis: int = 0) -> np.ndarray:
    """Quantile of the non-NaN values along `axis`, MATLAB `quantile` semantics.

    The sorted values are the (k - 0.5)/n quantiles, linear in between, clamped to
    the extremes: position p*n + 0.5, 1-based (Hyndman-Fan 5, numpy method 'hazen').
    All-NaN columns give NaN.
    """
    return quantile_ab(x, p, 0.5, 0.5, axis)


def quantile_ab(x: np.ndarray, p: float, a: float, b: float, axis: int = 0) -> np.ndarray:
    """Hyndman-Fan style quantile, 1-based position p*(n + 1 - a - b) + a, of the non-NaN values.

    Cells are grouped by their count n of valid values; within a group the two order
    statistics needed are found with one partition (NaN sorts last, so it never intrudes).
    """
    x = np.moveaxis(np.asarray(x), axis, 0)
    shp = x.shape[1:]
    xs = np.ascontiguousarray(x.reshape(x.shape[0], -1).T)
    n = np.sum(~np.isnan(xs), axis=1)
    out = np.full(xs.shape[0], np.nan)
    for u in np.unique(n):
        if u == 0:
            continue
        pos0 = min(max(p * (u + 1 - a - b) + a - 1.0, 0.0), u - 1.0)
        lo = int(np.floor(pos0))
        hi = min(lo + 1, int(u) - 1)
        frac = pos0 - lo
        idx = np.nonzero(n == u)[0]
        part = np.partition(xs[idx], sorted({lo, hi}), axis=1)
        vlo = part[:, lo].astype(np.float64)
        vhi = part[:, hi].astype(np.float64)
        out[idx] = vlo if frac == 0 else vlo + frac * (vhi - vlo)
    return out.reshape(shp)


def quantile_octave32(x: np.ndarray, p: float, axis: int = 0) -> np.ndarray:
    """Octave 9.2 `quantile(single(x), p)` (method 5) bit for bit: NaN ignored, 1-based position
    p*m + 0.5 clamped to [1, m-1] for the lower index, weight r clamped to [0, 1], and the value
    (1-r)*x_lo + r*x_hi evaluated in single precision (the double weights are rounded to single
    first, as Octave does for a double-by-single product). One valid value is duplicated.
    Returns float32; all-NaN columns give NaN."""
    x = np.moveaxis(np.asarray(x, np.float32), axis, 0)
    shp = x.shape[1:]
    xs = np.ascontiguousarray(x.reshape(x.shape[0], -1).T)
    n = np.sum(~np.isnan(xs), axis=1)
    out = np.full(xs.shape[0], np.nan, np.float32)
    for u in np.unique(n):
        if u == 0:
            continue
        pos = p * float(u) + 0.5
        lo1 = max(min(np.floor(pos), u - 1), 1)          # 1-based lower index
        r = max(min(pos - lo1, 1.0), 0.0)
        lo, hi = int(lo1) - 1, int(lo1)
        idx = np.nonzero(n == u)[0]
        part = np.sort(xs[idx], axis=1) if u > 1 else xs[idx]
        vlo = part[:, lo] if u > 1 else np.nanmax(part, axis=1)
        vhi = part[:, hi] if u > 1 else vlo
        out[idx] = np.float32(1.0 - r) * vlo + np.float32(r) * vhi
    return out.reshape(shp)


# Hyndman-Fan estimators as (alpha, beta) of position p*(n + 1 - alpha - beta) + alpha
# (1-based, linear in between). numpy's name -> (a, b); 'linear' = type 7, etc.
ESTIMATORS = {
    "weibull": (0.0, 0.0),
    "linear": (1.0, 1.0),
    "median_unbiased": (1 / 3, 1 / 3),
    "normal_unbiased": (3 / 8, 3 / 8),
    "hazen": (0.5, 0.5),
}


def circular_movmean(a: np.ndarray, width: int = SMOOTH_WIDTH) -> np.ndarray:
    """Centred circular moving mean along axis 0, ignoring NaN (NaN only if the whole window is).
    `width` must be odd and at most the length of the axis (detectc uses 31 on 366 days)."""
    n = a.shape[0]
    if width < 1 or width % 2 == 0 or width > n:
        raise ValueError(f"width {width} must be odd and between 1 and {n}")
    half = width // 2
    valid = ~np.isnan(a)
    v = np.where(valid, a, 0.0).astype(np.float64)
    out = np.zeros(a.shape, np.float64)
    cnt = np.zeros(a.shape, np.int32)
    for k in range(-half, half + 1):
        out += np.roll(v, -k, axis=0)
        cnt += np.roll(valid, -k, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        res = out / cnt
    return np.where(cnt > 0, res, np.nan)


def climatology(
    sst: np.ndarray,
    days: np.ndarray,
    *,
    baseline: tuple[int, int],
    p: float = PERCENTILE,
    half_window: int = HALF_WINDOW,
    smooth: int = SMOOTH_WIDTH,
    estimator: tuple[float, float] | str | None = None,
    precision: str = "float64",
) -> tuple[np.ndarray, np.ndarray]:
    """(m90, mclim), float64 (366, h, w), from whichever days are given.

    `baseline` is (first, last) global day index, inclusive. Days outside
    [first - half_window, last + half_window] are ignored; days missing from
    `days` are NaN. `estimator` = (a, b) of `quantile_ab`, or a numpy `method=` name; default MATLAB.
    `precision` "octave" emulates Octave's single-precision quantile and mean (module docstring).
    """
    if precision not in PRECISIONS:
        raise ValueError(f"precision {precision!r} not in {PRECISIONS}")
    if precision == "octave" and estimator is not None:
        raise ValueError("precision='octave' emulates the default MATLAB estimator only")
    days = np.asarray(days, dtype=np.int64)
    b0, b1 = baseline
    lo, hi = b0 - half_window, b1 + half_window
    keep = (days >= lo) & (days <= hi)
    h, w = sst.shape[1:]
    pdt = np.float32 if precision == "octave" else np.result_type(np.asarray(sst).dtype, np.float32)
    pad = np.full((hi - lo + 1, h, w), np.nan, pdt)  # input precision kept (S1 is float32)
    pad[days[keep] - lo] = sst[keep]
    pad_doy = doy366(np.arange(lo, hi + 1))
    centre = np.zeros(hi - lo + 1, bool)
    centre[half_window: half_window + (b1 - b0 + 1)] = True

    m90 = np.full((366, h, w), np.nan, np.float64)
    mclim = np.full((366, h, w), np.nan, np.float64)
    for i in range(366):
        if i == 59:
            continue
        cs = np.nonzero(centre & (pad_doy == i))[0]
        if cs.size == 0:
            continue
        member = np.zeros(pad.shape[0], bool)
        for c in cs:
            member[max(c - half_window, 0): c + half_window + 1] = True
        x = pad[member]
        if precision == "octave":
            m90[i] = quantile_octave32(x, p)
            cnt = np.sum(~np.isnan(x), axis=0)
            with np.errstate(invalid="ignore", divide="ignore"):
                mclim[i] = np.where(cnt > 0, np.nansum(x, axis=0, dtype=np.float64) / cnt, np.nan).astype(np.float32)
            continue
        if estimator is None:
            m90[i] = quantile_matlab(x, p)
        elif isinstance(estimator, str):
            with np.errstate(all="ignore"):
                m90[i] = np.nanquantile(x, p, axis=0, method=estimator)
        else:
            m90[i] = quantile_ab(x, p, *estimator)
        cnt = np.sum(~np.isnan(x), axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            mclim[i] = np.where(cnt > 0, np.nansum(x, axis=0, dtype=np.float64) / cnt, np.nan)
    for f in (m90, mclim):
        with np.errstate(all="ignore"):
            f[59] = np.nanmean(f[[58, 60]], axis=0)
    return circular_movmean(m90, smooth), circular_movmean(mclim, smooth)


def _runs(exceed: np.ndarray, min_duration: int, max_gap: int) -> np.ndarray:
    """Per-cell event state from an exceedance array (n, C): duration filter, then gap join."""
    n, c = exceed.shape
    x = np.zeros((c, n + 2), np.int8)
    x[:, 1:-1] = exceed.T
    d = np.diff(x, axis=1)  # (c, n+1): +1 where a run starts at t, -1 where it ended before t
    # row-major nonzero orders by cell, then time, so each cell's starts and ends alternate
    sc, st = np.nonzero(d == 1)
    _, et = np.nonzero(d == -1)  # et is the exclusive end
    keep = (et - st) >= min_duration
    sc, st, et = sc[keep], st[keep], et[keep]
    out = np.zeros((c, n + 1), np.int8)
    if sc.size:
        new = np.ones(sc.size, bool)
        new[1:] = (sc[1:] != sc[:-1]) | ((st[1:] - et[:-1]) > max_gap)
        first = np.nonzero(new)[0]
        last = np.append(first[1:] - 1, sc.size - 1)
        np.add.at(out, (sc[first], st[first]), 1)
        np.add.at(out, (sc[last], et[last]), -1)
    return (np.cumsum(out[:, :n], axis=1) > 0).T


def cell_events(
    sst: np.ndarray,
    threshold: np.ndarray,
    doy: np.ndarray,
    *,
    min_duration: int = MIN_DURATION,
    max_gap: int = MAX_GAP,
    precision: str = "float64",
) -> np.ndarray:
    """Per-cell MHW state (n, h, w) bool for contiguous daily `sst` (n, h, w).

    `threshold` is (366, h, w); `doy` (n,) the 366-calendar day-of-year of each day.
    The comparison `sst >= threshold` is made in float64, or for precision "octave" between
    single(sst) and single(threshold), as Octave compares a single with a double.
    """
    if precision not in PRECISIONS:
        raise ValueError(f"precision {precision!r} not in {PRECISIONS}")
    n, h, w = sst.shape
    dt_ = np.float32 if precision == "octave" else np.float64
    thr = np.asarray(threshold).astype(dt_, copy=False)[doy]
    with np.errstate(invalid="ignore"):
        exceed = np.asarray(sst).astype(dt_, copy=False) >= thr
    return _runs(exceed.reshape(n, h * w), min_duration, max_gap).reshape(n, h, w)
