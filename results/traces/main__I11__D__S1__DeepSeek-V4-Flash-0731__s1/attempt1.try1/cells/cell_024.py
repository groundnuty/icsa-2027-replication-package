
import numpy as np

# Load data
hot = None  # Need to recompute or load
# Let me recompute hot from saved data

import pandas as pd
from datetime import date

smooth_thresholds = np.load('/work/smooth_thresholds.npy')
sea_mask = np.load('/work/sea_mask.npy')
target_sst = np.load('/work/target_sst.npy')

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values
target_idx = np.where((time_vals >= np.datetime64('2021-06-01')) & (time_vals <= np.datetime64('2021-08-31')))[0]
target_time = time_vals[target_idx]
target_dates = [pd.Timestamp(t).date() for t in target_time]

def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

target_doy = np.array([day_of_year_366(d) for d in target_dates])
n_time = len(target_dates)
n_lat, n_lon = 60, 60

target_thresholds = smooth_thresholds[target_doy - 1]

hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_mask[i, j]:
                sst = target_sst[t, i, j]
                if not np.isnan(sst):
                    thresh = target_thresholds[t, i, j]
                    if not np.isnan(thresh):
                        hot[t, i, j] = (sst >= thresh)

# Now find per-cell MHWs
# For each cell, find runs of >=5 consecutive hot days
# Join runs separated by 1-2 non-hot days

# mhw_mask[time, i, j] = 1 if cell is inside a per-cell MHW on that day
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        
        # Get the hot sequence for this cell
        hot_seq = hot[:, i, j].astype(int)
        
        # Find runs of hot days
        # First, identify runs of at least 5 consecutive hot days
        # Then join runs separated by 1-2 non-hot days
        
        # Find all hot days
        hot_days = np.where(hot_seq == 1)[0]
        if len(hot_days) == 0:
            continue
        
        # Find contiguous runs
        runs = []
        start = hot_days[0]
        prev = hot_days[0]
        for d in hot_days[1:]:
            if d > prev + 1:
                runs.append((start, prev))
                start = d
            prev = d
        runs.append((start, prev))
        
        # Filter runs with length >= 5
        long_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        if not long_runs:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined_runs = [list(long_runs[0])]
        for s, e in long_runs[1:]:
            last_e = joined_runs[-1][1]
            gap = s - last_e - 1
            if 1 <= gap <= 2:
                joined_runs[-1][1] = e  # Extend
            else:
                joined_runs.append([s, e])
        
        # Mark days in joined runs as MHW
        for s, e in joined_runs:
            mhw_mask[s:e+1, i, j] = 1

print(f"MHW cells per day: {mhw_mask.sum(axis=(1,2))}")
print(f"Total MHW cell-days: {mhw_mask.sum()}")

# Save
np.save('/work/mhw_mask.npy', mhw_mask)
np.save('/work/hot.npy', hot)
print("Saved.")
