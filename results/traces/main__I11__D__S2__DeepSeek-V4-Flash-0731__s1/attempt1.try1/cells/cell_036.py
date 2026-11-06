
import numpy as np
from datetime import date
from collections import defaultdict
import xarray as xr
import pandas as pd

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_ext.analysed_sst.values.astype(np.float64)
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

sea_mask = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", sea_mask.sum())

# Day of year
CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

# Build pools
baseline_mask = np.array([(date(1992,1,1) <= d <= date(2002,12,31)) for d in baseline_dates])
baseline_idx = np.where(baseline_mask)[0]

pool_indices = defaultdict(list)
for bi in baseline_idx:
    b = baseline_dates[bi]
    b_doy = get_doy(b)
    if b_doy == 60:
        continue
    lo = max(0, bi - 5)
    hi = min(len(baseline_dates)-1, bi + 5)
    pool_indices[b_doy].extend(list(range(lo, hi+1)))

# Compute threshold and climatology
sea_flat = sea_mask.flatten()
sea_pos = np.where(sea_flat)[0]

threshold = np.zeros((366, 60, 60), dtype=np.float64)
climatology = np.zeros((366, 60, 60), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices.get(d, [])
    if not idx:
        continue
    idx = np.array(idx)
    sst_sub = baseline_sst[idx]
    sst_flat = sst_sub.reshape(len(idx), -1)
    sst_sea = sst_flat[:, sea_pos]
    pct = np.nanpercentile(sst_sea, 90, axis=0, method='hazen')
    mean = np.nanmean(sst_sea, axis=0)
    threshold[d-1].flat[sea_pos] = pct
    climatology[d-1].flat[sea_pos] = mean

# Day 60 = mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# Smooth with 31-day centered moving mean wrapping around year
def smooth_wrap(arr):
    result = np.zeros_like(arr)
    for i in range(366):
        indices = [(i + offset) % 366 for offset in range(-15, 16)]
        result[i] = np.mean(arr[indices], axis=0)
    return result

threshold_smooth = smooth_wrap(threshold)
climatology_smooth = smooth_wrap(climatology)

print("Thresholds and climatology computed")

# Compute hot days
target_doy = np.array([get_doy(d) for d in target_dates])
n_time = len(target_dates)

hot = np.zeros((60, 60, n_time), dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    hot[:, :, t] = (target_sst[t] >= threshold_smooth[doy-1]) & sea_mask

print("Hot days computed")

# Find per-cell MHWs (corrected algorithm)
mhw_mask = np.zeros((60, 60, n_time), dtype=bool)

for i in range(60):
    for j in range(60):
        if not sea_mask[i, j]:
            continue
        cell_hot = hot[i, j, :]
        
        # Find all maximal runs of consecutive hot days
        runs = []
        t = 0
        while t < n_time:
            if cell_hot[t]:
                start = t
                while t < n_time and cell_hot[t]:
                    t += 1
                runs.append((start, t-1))
            else:
                t += 1
        
        # Identify MHW runs (length >= 5)
        mhw_indices = [k for k, (s, e) in enumerate(runs) if e - s + 1 >= 5]
        
        if not mhw_indices:
            continue
        
        # Merge consecutive MHWs separated by 1-2 non-hot days
        events = []
        current = [runs[mhw_indices[0]][0], runs[mhw_indices[0]][1]]
        current_ri = mhw_indices[0]
        
        for ri in mhw_indices[1:]:
            mhw_start, mhw_end = runs[ri]
            total_days = mhw_start - current[1] - 1
            hot_days_between = 0
            for k in range(current_ri + 1, ri):
                hot_days_between += runs[k][1] - runs[k][0] + 1
            non_hot_days = total_days - hot_days_between
            
            if 1 <= non_hot_days <= 2:
                current[1] = mhw_end
                current_ri = ri
            else:
                events.append(tuple(current))
                current = [mhw_start, mhw_end]
                current_ri = ri
        
        events.append(tuple(current))
        
        for start, end in events:
            mhw_mask[i, j, start:end+1] = True

print("Per-cell MHWs computed")
print("MHW mask count:", mhw_mask.sum())

# Save
np.save('/work/mhw_mask_corrected.npy', mhw_mask)
np.save('/work/hot_corrected.npy', hot)
