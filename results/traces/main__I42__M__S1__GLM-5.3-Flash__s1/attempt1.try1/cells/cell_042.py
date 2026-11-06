import numpy as np, h5py
from datetime import date, timedelta

sst_t = np.load("/work/sst_target_corr.npy").astype(np.float64)
thr_s = np.load("/work/thr_smooth_corr.npy")
MD_CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)
doys = np.array([MD_CUM[t.month-1]+t.day for t in target_dates])

# sea cells: SST finite on every target day
sea_mask = np.isfinite(sst_t).all(axis=0)
print("sea cells:", sea_mask.sum(), " land:", (~sea_mask).sum())

# hot days
thr_target = thr_s[doys-1]
with np.errstate(invalid="ignore"):
    hot = (sst_t >= thr_target) & sea_mask[None]
print("hot day-cells:", hot.sum())

# per-cell MHW
def mhw_mask(hs, min_run=5, max_gap=2):
    n = len(hs)
    runs = []
    i = 0
    while i < n:
        if hs[i]:
            j = i
            while j < n and hs[j]:
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
per_cell_events = {}
for ii in range(60):
    for jj in range(60):
        if hot[:,ii,jj].any():
            m, runs, merged = mhw_mask(hot[:,ii,jj])
            mhw[:,ii,jj] = m
            if merged:
                per_cell_events[(ii,jj)] = merged
print("cells with per-cell MHW:", len(per_cell_events))
print("total MHW day-cells:", mhw.sum())

# regional events
active = mhw.any(axis=(1,2))
idx = np.where(active)[0]
events = []
if len(idx):
    start = prev = idx[0]
    for k in idx[1:]:
        if k == prev+1: prev = k
        else: events.append((start, prev)); start = prev = k
    events.append((start, prev))
print("active day indices:", list(map(int, idx)))
print("regional events:", [(target_dates[a].isoformat(), target_dates[b].isoformat()) for a,b in events])
np.save("/work/mhw_final_corr.npy", mhw)
