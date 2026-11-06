import numpy as np
import datetime as dt
import json, os

# ---------- date helpers ----------
def date_list(start, end):
    d = start; out=[]
    while d <= end:
        out.append(d); d += dt.timedelta(days=1)
    return out

base_dates  = date_list(dt.date(1991,12,27), dt.date(2003,1,5))   # extended baseline window
target_dates = date_list(dt.date(2009,6,1), dt.date(2009,8,31))
Tb, Tt = len(base_dates), len(target_dates)
base_idx = {d: i for i, d in enumerate(base_dates)}

# day-of-year mapping: leap-year based (1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, 31 Dec=366)
md = [31,29,31,30,31,30,31,31,30,31,30,31]
cum = [0]
for x in md: cum.append(cum[-1]+x)
def doy_of(d):  # d: date
    return cum[d.month-1] + d.day
def md_of(doy):
    for m in range(12):
        if cum[m] < doy <= cum[m+1]:
            return m+1, doy - cum[m]

# ---------- load data ----------
N = 60*60
base_arr  = np.empty((Tb, N), dtype=np.float64)
for i, d in enumerate(base_dates):
    base_arr[i] = np.load(f"/work/region/{d:%Y%m%d}.npy").ravel()
target_arr = np.empty((Tt, N), dtype=np.float64)
for i, d in enumerate(target_dates):
    target_arr[i] = np.load(f"/work/region/{d:%Y%m%d}.npy").ravel()
print("loaded", base_arr.shape, target_arr.shape)
print("base nan frac", np.isnan(base_arr).mean().round(4), "target nan frac", np.isnan(target_arr).mean().round(4))

# ---------- sea cells ----------
sea = np.all(np.isfinite(target_arr), axis=0)
print("sea cells:", int(sea.sum()), "of", N)

# ---------- pools per day of year ----------
doy_target = np.array([doy_of(d) for d in target_dates])
print("target doys:", doy_target.min(), doy_target.max())

pool_idx = {}   # d -> array of global baseline indices
for d in range(1, 367):
    if d == 60:
        continue
    m, day = md_of(d)
    s = set()
    for y in range(1992, 2003):
        B = dt.date(y, m, day)
        for k in range(-5, 6):
            T = B + dt.timedelta(days=k)
            if dt.date(1991,12,27) <= T <= dt.date(2003,1,5):
                s.add(base_idx[T])
    pool_idx[d] = np.array(sorted(s), dtype=np.int64)
lens = [len(v) for v in pool_idx.values()]
print("pool sizes min/med/max:", min(lens), int(np.median(lens)), max(lens))

# ---------- threshold (hazen 90pct) and climatology (mean) ----------
thr_raw = np.full((N, 366), np.nan)
cli_raw = np.full((N, 366), np.nan)
allnan_cells_thr = 0
for d, idx in pool_idx.items():
    V = base_arr[idx, :].T          # (N, L)
    with np.errstate(invalid='ignore'):
        thr = np.nanpercentile(V, 90, axis=1, method='hazen')
        cli = np.nanmean(V, axis=1)
    thr_raw[:, d-1] = thr
    cli_raw[:, d-1] = cli
    allnan_cells_thr += int(np.isnan(thr).sum())
# day 60: mean of days 59 and 61
for arr in (thr_raw, cli_raw):
    arr[:, 59] = 0.5 * (arr[:, 58] + arr[:, 60])
print("cells with any all-NaN pool (NaN in raw thr):", allnan_cells_thr)

# ---------- centred 31-day wrapping moving mean ----------
def smooth31(arr):   # arr: (N, 366)
    ext = np.concatenate([arr[:, -15:], arr, arr[:, :15]], axis=1)  # (N, 397)
    from numpy.lib.stride_tricks import sliding_window_view
    sw = sliding_window_view(ext, 31, axis=1)   # (N, 366, 31)
    return sw.mean(axis=2)

thr = smooth31(thr_raw)
cli = smooth31(cli_raw)
print("thr sample (sea cell 0):", thr[0][[151,152,153]], "cli sample:", cli[0][[151,152,153]])
print("thr range over sea cells:", np.nanmin(thr[sea]), np.nanmax(thr[sea]))
np.save('/work/thr.npy', thr)
np.save('/work/cli.npy', cli)
np.save('/work/sea.npy', sea)
np.save('/work/target_arr.npy', target_arr)
np.save('/work/doy_target.npy', doy_target)
print("saved intermediates")
