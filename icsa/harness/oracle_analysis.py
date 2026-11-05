"""The oracle agent's analysis: a LITERAL implementation of the Method in protocol/task-prompt.md.

Written from the prompt text only, never from #4's code (this module must not import
icsa.refdet or anything else of the reference implementation). Each step quotes the sentence it
implements. Where the text is silent a choice is made and marked ASSUMPTION; a mismatch with the
ground truth on the 50 instances means the prompt is under-specified there and is REPORTED, not
fixed by looking at #4.

Self-contained on purpose (numpy, netCDF4, stdlib): the oracle ships this file's source into the
sandbox and runs it there, through the option's data path.
"""
from __future__ import annotations

import datetime
import json
import os
import warnings

import numpy as np

BASELINE = (datetime.date(1992, 1, 1), datetime.date(2002, 12, 31))   # "baseline years 1992-2002", "(1992-01-01 to 2002-12-31)"
EXTENDED = (datetime.date(1991, 12, 27), datetime.date(2003, 1, 5))   # "Windows near the ends of the baseline reach up to 5 days beyond it"
HALF_WINDOW = 5


def day_of_year(d: datetime.date) -> int:
    """"Map every date to a day of year from 1 to 366 by month and day: 1 January = 1,
    28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366. Non-leap years have
    no day 60." -> the day of year the same month and day has in a leap year."""
    return datetime.date(2000, d.month, d.day).timetuple().tm_yday


def sea_cells(sst: np.ndarray) -> np.ndarray:
    """"*Sea cells* are the region's grid cells whose SST is finite on every day of the target period."
    sst holds exactly the target days. (Baseline values of a sea cell may still be NaN: the pools ignore NaN.)"""
    return np.isfinite(sst).all(axis=0)


def needed_doys(start: datetime.date, end: datetime.date) -> tuple[set, set]:
    """The days of year whose thresholds the target period uses, worked back from the Method:
    a target day's threshold is the smoothed value of its day of year d, which averages the unsmoothed values of
    days d-15 ... d+15 (counted modulo 366) ("a centred 31-day moving mean that wraps around the year"); day 60's
    unsmoothed value is the mean of days 59 and 61. Every other day of year d has its own pool. Reading taken: it is
    enough to compute (and so to read the data for) the days of year that these values depend on; the others are
    never used by a target day, so the result is the same as computing all 366. Returns (unsmoothed days needed,
    days with a pool)."""
    tdoys = {day_of_year(start + datetime.timedelta(days=i)) for i in range((end - start).days + 1)}
    raw = {((d - 1 + s) % 366) + 1 for d in tdoys for s in range(-15, 16)}
    if 60 in raw:
        raw |= {59, 61}
    return raw, raw - {60}


def needed_baseline_dates(start: datetime.date, end: datetime.date) -> list:
    """The dates the pools of `needed_doys` draw on: +-5 calendar days around every baseline date
    (1992-01-01 to 2002-12-31) whose day of year has a needed pool."""
    _, pooled = needed_doys(start, end)
    out = set()
    d = BASELINE[0]
    while d <= BASELINE[1]:
        if day_of_year(d) in pooled:
            out.update(d + datetime.timedelta(days=o) for o in range(-HALF_WINDOW, HALF_WINDOW + 1))
        d += datetime.timedelta(days=1)
    return sorted(out)


def date_ranges(dates: list) -> list:
    """Inclusive (first, last) ranges of consecutive dates."""
    out = []
    for d in dates:
        if out and d - out[-1][1] == datetime.timedelta(days=1):
            out[-1][1] = d
        else:
            out.append([d, d])
    return [(a, b) for a, b in out]


def pooled_stats(sst: np.ndarray, dates: list, pooled: set | None = None) -> tuple[np.ndarray, np.ndarray]:
    """"For each day of year d other than 60, the pool is every SST value whose date lies within +-5
    calendar days of a baseline date (1992-01-01 to 2002-12-31) whose day of year is d. Windows near the
    ends of the baseline reach up to 5 days beyond it; include those days. 29 February values belong to
    the windows of their calendar neighbours. Day 60 gets no pool of its own."
    Reading taken: the window is +-5 calendar dates (so the 29 Feb of a leap year is a member of the windows
    of the baseline dates 24 Feb-5 Mar around it, by its date); no wrap around the year, as the window is
    on dates. A value is in at most one window per day of year (same-day-of-year baseline dates are a
    year apart), so no value counts twice.
    "The threshold is the 90th percentile of the pool, ... numpy's method="hazen", ignoring NaN.
    The climatology is the mean of the pool, ignoring NaN." Returns (366, cells) arrays; row 59 (day 60) is NaN.
    sst: (days, cells); dates: the matching dates (they must include every window day of the pooled days of year);
    pooled: the days of year to compute (default: all but 60); the other rows stay NaN."""
    index = {d: i for i, d in enumerate(dates)}
    ncell = sst.shape[1]
    pooled = set(range(1, 367)) - {60} if pooled is None else set(pooled) - {60}
    members: dict[int, list[int]] = {k: [] for k in pooled}
    d = BASELINE[0]
    while d <= BASELINE[1]:
        k = day_of_year(d)
        if k in pooled:
            for off in range(-HALF_WINDOW, HALF_WINDOW + 1):
                members[k].append(index[d + datetime.timedelta(days=off)])   # KeyError = a window day is missing
        d += datetime.timedelta(days=1)
    thr = np.full((366, ncell), np.nan)
    clim = np.full((366, ncell), np.nan)
    for k, idx in members.items():
        pool = sst[idx]
        with warnings.catch_warnings():      # an all-NaN pool gives NaN (no threshold: nothing is hot there)
            warnings.simplefilter("ignore", RuntimeWarning)
            thr[k - 1] = np.nanpercentile(pool, 90, axis=0, method="hazen")
            clim[k - 1] = np.nanmean(pool, axis=0)
    return thr, clim


def fix_leap_day_and_smooth(x: np.ndarray) -> np.ndarray:
    """"In both the threshold and the climatology, set day 60 to the mean of days 59 and 61. Then smooth each
    of them, as a 366-element array, with an unweighted centred 31-day moving mean that wraps around the year
    (day d averages days d-15 ... d+15, counted modulo 366)." x: (366, cells).
    Reading taken: the text says "ignoring NaN" only for the pooled percentile and mean, so these two means are
    plain arithmetic means (a NaN in day 59 or 61, or in the window, propagates). AMBIGUITY to report: the
    authors' code may ignore NaN here; a mismatch with the ground truth on the 50 instances would show it."""
    x = x.copy()
    x[59] = (x[58] + x[60]) / 2.0                           # index 59 is day 60
    return sum(np.roll(x, s, axis=0) for s in range(-15, 16)) / 31.0


def cell_mhw_days(hot: np.ndarray) -> np.ndarray:
    """"a per-cell MHW is a run of at least 5 consecutive hot days; per-cell MHWs separated by at
    most 2 days are joined into one, and the gap days belong to it." hot: 1-D bool over target days."""
    n = len(hot)
    out = np.zeros(n, bool)
    d = np.diff(np.concatenate(([0], hot.astype(np.int8), [0])))
    runs = [[int(a), int(b) - 1] for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= 5]
    joined: list[list[int]] = []
    for a, b in runs:
        if joined and a - joined[-1][1] - 1 <= 2:
            joined[-1][1] = b
        else:
            joined.append([a, b])
    for a, b in joined:
        out[a:b + 1] = True
    return out


def regional_events(active: np.ndarray) -> list[tuple[int, int]]:
    """"a day is active if at least one sea cell of the region is inside a per-cell MHW on that
    day; a regional MHW event is a maximal run of consecutive active days." Returns index pairs."""
    d = np.diff(np.concatenate(([0], active.astype(np.int8), [0])))
    return [(int(a), int(b) - 1) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1))]


def analyse(sst, dates, start: datetime.date, end: datetime.date):
    """sst: (days, lat, lon) kelvin over the region's cells, for the baseline days of `needed_baseline_dates` (or more)
    and the target period; dates: the matching datetime.date list. Returns (mask uint8 (target days, lat, lon), target dates, events)."""
    if any(b <= a for a, b in zip(dates, dates[1:])):
        raise ValueError("dates must be strictly increasing (no duplicates)")   # target after baseline; no overlap
    sst = np.asarray(sst, dtype=np.float64)                    # "in double precision (float64)"
    nt, nlat, nlon = sst.shape
    in_target = np.array([start <= d <= end for d in dates])
    sea = sea_cells(sst[in_target])                            # step 1
    flat = sst[:, sea]                                         # (days, sea cells)
    doy = np.array([day_of_year(d) for d in dates])
    _, pooled = needed_doys(start, end)
    is_base = np.array([d < start for d in dates])    # every loaded day before the target period
    try:
        thr, _clim = pooled_stats(flat[is_base], [d for d, m in zip(dates, is_base) if m], pooled)   # step 2 (the climatology is not used further)
    except KeyError as e:
        raise ValueError(f"a window day of the baseline pools was not loaded: {e}") from None
    thr = fix_leap_day_and_smooth(thr)
    _clim = fix_leap_day_and_smooth(_clim)                     # "In both the threshold and the climatology" (not consumed further)
    # step 3: "Restrict SST to {START}-{END} before finding hot runs and joining gaps"
    tdates = [d for d, m in zip(dates, in_target) if m]
    tsst, tdoy = flat[in_target], doy[in_target]
    hot = tsst >= thr[tdoy - 1]                                # "SST greater than or equal to the threshold"
    cell = np.zeros_like(hot)
    for c in range(hot.shape[1]):
        cell[:, c] = cell_mhw_days(hot[:, c])
    mask = np.zeros((len(tdates), nlat, nlon), np.uint8)       # land cells are 0
    mask[:, sea] = cell
    ev = regional_events(cell.any(axis=1)) if cell.size else []   # step 4
    return mask, tdates, [(tdates[a], tdates[b]) for a, b in ev]


def write_outputs(out_dir: str, mask, tdates, events, lat, lon, region: dict, start, end, baseline_used=None) -> None:
    """"Results": output/mhw_mask.nc (variable mhw, uint8, (time, lat, lon), dataset coordinate
    values) and output/report.json with exactly the six stated fields."""
    import netCDF4
    os.makedirs(out_dir, exist_ok=True)
    ds = netCDF4.Dataset(os.path.join(out_dir, "mhw_mask.nc"), "w")
    ds.createDimension("time", len(tdates)); ds.createDimension("lat", len(lat)); ds.createDimension("lon", len(lon))
    t = ds.createVariable("time", "i4", ("time",)); t.units = "days since 1982-01-01"; t.calendar = "standard"
    t[:] = [(d - datetime.date(1982, 1, 1)).days for d in tdates]
    ds.createVariable("lat", "f8", ("lat",))[:] = lat
    ds.createVariable("lon", "f8", ("lon",))[:] = lon
    ds.createVariable("mhw", "u1", ("time", "lat", "lon"))[:] = mask
    ds.close()
    report = {"region": region,
              # reading taken: "the first and last baseline day your threshold and climatology used" = the pooled days,
              # which reach 5 days beyond the baseline
              # ruling (science agent, 1 Nov): a single envelope of the baseline days actually used; no list format
              "baseline_analysed": ({"start": baseline_used[0].isoformat(), "end": baseline_used[-1].isoformat()}
                                    if baseline_used else None),
              "target_analysed": {"start": start.isoformat(), "end": end.isoformat()},
              "events": [{"onset": a.isoformat(), "end": b.isoformat()} for a, b in events],
              "complete": True, "caveats": ""}
    with open(os.path.join(out_dir, "report.json"), "w") as fh:
        json.dump(report, fh, allow_nan=False)


def run(load_region, region: dict, start: datetime.date, end: datetime.date, out_dir: str = "output") -> int:
    """load_region(lat_min, lat_max, lon_min, lon_max, date_ranges) -> (sst (days, lat, lon), dates, lat, lon):
    the days inside the inclusive ranges, over the cells inside the inclusive bounds, read through the
    option's path. The days asked for are the baseline days the target period's thresholds draw on
    (`needed_baseline_dates`) and the target period, and nothing else."""
    base = needed_baseline_dates(start, end)
    sst, dates, lat, lon = load_region(region["lat_min"], region["lat_max"], region["lon_min"], region["lon_max"],
                                       date_ranges(base) + [(start, end)])
    mask, tdates, events = analyse(sst, dates, start, end)
    write_outputs(out_dir, mask, tdates, events, lat, lon, region, start, end, base)
    print("events", len(events), "mask", mask.shape)
    return len(events)
