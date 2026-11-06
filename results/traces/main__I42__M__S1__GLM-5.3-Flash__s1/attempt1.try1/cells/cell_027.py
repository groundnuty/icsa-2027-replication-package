import numpy as np, pickle, h5py, json, os
from datetime import date, timedelta

hot_finite = np.load("/work/hot_finite.npy")
sst_t = np.load("/work/sst_target.npy")
with open("/work/window_dates.pkl","rb") as f:
    wd = pickle.load(f)
lat_idx, lon_idx = wd["lat_idx"], wd["lon_idx"]
i0, i1 = lat_idx[0], lat_idx[-1]+1
j0, j1 = lon_idx[0], lon_idx[-1]+1
with h5py.File("/data/icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc","r") as f:
    lat = f["latitude"][:].astype(np.float64)
    lon = f["longitude"][:].astype(np.float64)
lat_reg = lat[i0:i1]; lon_reg = lon[j0:j1]

target_dates = []
d = date(2012,6,1)
while d <= date(2012,8,31):
    target_dates.append(d); d += timedelta(days=1)

def mhw_mask(hot_series, min_run=5, max_gap=2):
    n = len(hot_series)
    # runs
    runs = []
    i = 0
    while i < n:
        if hot_series[i]:
            j = i
            while j < n and hot_series[j]:
                j += 1
            runs.append([i, j-1])
            i = j
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
    return mask

# per-cell MHW mask (92,60,60)
mhw = np.zeros_like(hot_finite)
for ii in range(60):
    for jj in range(60):
        if hot_finite[:,ii,jj].any():
            mhw[:,ii,jj] = mhw_mask(hot_finite[:,ii,jj])

print("total per-cell MHW days:", mhw.sum())
active = mhw.any(axis=(1,2))
print("active days:", np.where(active)[0], "count:", active.sum())
idx = np.where(active)[0]
# regional events: maximal consecutive runs of active days
events = []
if len(idx):
    start = idx[0]; prev = idx[0]
    for k in idx[1:]:
        if k == prev + 1:
            prev = k
        else:
            events.append((start, prev)); start = k; prev = k
    events.append((start, prev))
print("events:", events)
for a,b in events:
    print(f"  event: {target_dates[a]} .. {target_dates[b]} ({b-a+1} days)")
np.save("/work/mhw_mask.npy", mhw)
