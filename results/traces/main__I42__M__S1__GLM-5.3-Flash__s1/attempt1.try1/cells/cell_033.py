import numpy as np, pickle, h5py
from datetime import date, timedelta

thr_s = np.load("/work/thr_smooth2.npy")
sst_t = np.load("/work/sst_target.npy")   # (92,60,60) float64

MD_CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1] + t.day for t in target_dates])

# sea cells: finite on every target day
sea_mask = np.isfinite(sst_t).all(axis=0)
print("sea cells:", sea_mask.sum())

thr_target = thr_s[doys - 1]
with np.errstate(invalid="ignore"):
    hot = (sst_t >= thr_target) & sea_mask[None,:,:]
print("hot day-cells:", hot.sum())

def mhw_mask(hot_series, min_run=5, max_gap=2):
    n = len(hot_series)
    runs = []
    i = 0
    while i < n:
        if hot_series[i]:
            j = i
            while j < n and hot_series[j]:
                j += 1
            runs.append([i, j-1]); i = j
        else:
            i += 1
    mhw_runs = [r for r in runs if r[1]-r[0]+1 >= min_run]
    merged = []
    for r in mhw_runs:
        if merged and r[0]-merged[-1][1]-1 <= max_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    mask = np.zeros(n, dtype=bool)
    for a,b in merged:
        mask[a:b+1] = True
    return mask, runs, merged

mhw = np.zeros_like(hot)
n_cells_with_mhw = 0
for ii in range(60):
    for jj in range(60):
        if hot[:,ii,jj].any():
            m, runs, merged = mhw_mask(hot[:,ii,jj])
            mhw[:,ii,jj] = m
            if m.any(): n_cells_with_mhw += 1
print("cells with any per-cell MHW:", n_cells_with_mhw)
print("total MHW day-cells:", mhw.sum())

active = mhw.any(axis=(1,2))
idx = np.where(active)[0]
events = []
if len(idx):
    start = prev = idx[0]
    for k in idx[1:]:
        if k == prev+1: prev = k
        else: events.append((start, prev)); start = prev = k
    events.append((start, prev))
print("active days:", list(idx))
print("events (target idx):", events)
for a,b in events:
    print(f"  {target_dates[a].isoformat()} .. {target_dates[b].isoformat()}  ({b-a+1} days)")
np.save("/work/mhw_final.npy", mhw)
