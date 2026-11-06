
import numpy as np
import pandas as pd
import json
import xarray as xr
import os

# Load all data
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')
base_times = np.load('/work/base_times.npy')
targ_times = np.load('/work/targ_times.npy')
thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')

base_dates = pd.DatetimeIndex(base_times)
targ_dates = pd.DatetimeIndex(targ_times)

n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
n_targ = len(targ_dates)

print(f"Target days: {n_targ}")
print(f"Grid: {n_lat} x {n_lon}")

# Day of year mapping
def date_to_doy(dt):
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

targ_doy = np.array([date_to_doy(d) for d in targ_dates])

# Sea cells
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        if np.all(np.isfinite(target_sst[:, i, j])):
            sea_cells[i, j] = True

print(f"Sea cells: {sea_cells.sum()}")

# Determine hot days per cell
hot = np.zeros((n_targ, n_lat, n_lon), dtype=bool)

for t in range(n_targ):
    d = targ_doy[t]
    thr = thresholds[d-1, :, :]
    sst_t = target_sst[t, :, :].astype(np.float64)
    hot[t] = (sst_t >= thr) & sea_cells & np.isfinite(sst_t) & np.isfinite(thr)

# Find per-cell MHWs
mhw_mask = np.zeros((n_targ, n_lat, n_lon), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        hot_series = hot[:, i, j]
        
        # Find hot runs
        runs = []
        t = 0
        while t < n_targ:
            if hot_series[t]:
                start = t
                while t < n_targ and hot_series[t]:
                    t += 1
                end = t - 1
                runs.append((start, end))
            else:
                t += 1
        
        if len(runs) == 0:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        joined = [list(runs[0])]
        for k in range(1, len(runs)):
            gap = runs[k][0] - joined[-1][1] - 1
            if gap <= 2:
                joined[-1][1] = runs[k][1]
            else:
                joined.append(list(runs[k]))
        
        # Check if joined runs are >= 5 days
        for start, end in joined:
            if end - start + 1 >= 5:
                mhw_mask[start:end+1, i, j] = True

# Regional events
active = mhw_mask.any(axis=(1, 2))

# Find maximal runs of consecutive active days
events = []
t = 0
while t < n_targ:
    if active[t]:
        start = t
        while t < n_targ and active[t]:
            t += 1
        end = t - 1
        events.append((start, end))
    else:
        t += 1

print(f"\nRegional events:")
event_list = []
for start, end in events:
    onset = targ_dates[start].strftime('%Y-%m-%d')
    end_date = targ_dates[end].strftime('%Y-%m-%d')
    print(f"  {onset} to {end_date} ({end - start + 1} days)")
    event_list.append({"onset": onset, "end": end_date})

print(f"\nTotal events: {len(events)}")
print(f"mhw_mask shape: {mhw_mask.shape}")
print(f"mhw_mask sum: {mhw_mask.sum()}")

# Also verify the mask covers the correct days
active_days = np.where(active)[0]
print(f"Active day indices: {active_days}")
for t in active_days:
    print(f"  Day {t}: {targ_dates[t].strftime('%Y-%m-%d')}")
