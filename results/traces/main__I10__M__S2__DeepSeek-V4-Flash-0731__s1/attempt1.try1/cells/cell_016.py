
import numpy as np
from datetime import date, timedelta
from collections import defaultdict
import xarray as xr
import pandas as pd
import json
import os
import warnings

# ===== Load data =====
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat_all = ds['latitude'].values
lon_all = ds['longitude'].values
time_all = ds['time'].values
time_dates = pd.to_datetime(time_all).date

lat_mask = (lat_all >= 55.67) & (lat_all <= 56.87)
lon_mask = (lon_all >= 16.45) & (lon_all <= 17.65)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
region_lat = lat_all[lat_idx]
region_lon = lon_all[lon_idx]

pool_start = date(1991, 12, 27)
pool_end = date(2003, 1, 5)
target_start = date(2005, 6, 1)
target_end = date(2005, 8, 31)

pool_mask = (time_dates >= pool_start) & (time_dates <= pool_end)
target_mask = (time_dates >= target_start) & (time_dates <= target_end)
time_idx = np.where(pool_mask | target_mask)[0]

sst = ds['analysed_sst'].isel(time=time_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

pool_local = np.where(pool_mask[time_idx])[0]
target_local = np.where(target_mask[time_idx])[0]

target_time = time_all[time_idx[target_local]]

# ===== Sea cells =====
target_sst = sst[target_local]
sea_cells = np.all(np.isfinite(target_sst), axis=0)
n_sea = int(sea_cells.sum())
print(f"Sea cells: {n_sea} of {sea_cells.size}")

# ===== Day of year mapping =====
def doy_map(d):
    months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(months[:d.month-1]) + d.day

# ===== Build pools =====
baseline_dates_set = set()
d = date(1992, 1, 1)
while d <= date(2002, 12, 31):
    baseline_dates_set.add(d)
    d += timedelta(days=1)

pool_dates_actual = []
d = date(1991, 12, 27)
while d <= date(2003, 1, 5):
    pool_dates_actual.append(d)
    d += timedelta(days=1)

doy_to_pool_idx = defaultdict(list)
for pi, t in enumerate(pool_dates_actual):
    for offset in range(-5, 6):
        b = t + timedelta(days=offset)
        if b in baseline_dates_set:
            dd = doy_map(b)
            if dd != 60:
                doy_to_pool_idx[dd].append(pi)

doy_to_pool_idx_arr = {d: np.array(idx) for d, idx in doy_to_pool_idx.items()}

# ===== Compute thresholds and climatology =====
n_doy = 366
n_lat, n_lon = 60, 60
pool_sst = sst[pool_local]

thresholds = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, n_doy + 1):
        if d == 60:
            continue
        idx = doy_to_pool_idx_arr[d]
        if len(idx) == 0:
            continue
        pool_data = pool_sst[idx]
        
        valid = np.isfinite(pool_data) & sea_cells[None, :, :]
        counts = valid.sum(axis=0)
        
        sums = np.where(valid, pool_data, 0.0).sum(axis=0)
        climatology[d-1] = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
        
        valid_cells = sea_cells & (counts > 0)
        for ci in range(n_lat):
            for cj in range(n_lon):
                if valid_cells[ci, cj]:
                    vals = pool_data[:, ci, cj]
                    vals_valid = vals[valid[:, ci, cj]]
                    thresholds[d-1, ci, cj] = np.percentile(vals_valid, 90, method='hazen')

# Set day 60 = mean of days 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# ===== Smoothing =====
def smooth_wrap(arr):
    n = 366
    result = np.zeros_like(arr)
    for d in range(n):
        indices = [(d + k) % n for k in range(-15, 16)]
        window = arr[indices]
        valid = np.isfinite(window)
        counts = valid.sum(axis=0)
        sums = np.where(valid, window, 0.0).sum(axis=0)
        result[d] = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
    return result

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

# Verify no NaN for sea cells after smoothing
sea_nan_thresh = np.isnan(thresholds_smooth[:, sea_cells])
sea_nan_clim = np.isnan(climatology_smooth[:, sea_cells])
print(f"NaN smoothed thresholds among sea cells: {sea_nan_thresh.sum()}")
print(f"NaN smoothed climatology among sea cells: {sea_nan_clim.sum()}")

# ===== Target day-of-year =====
target_dates = [time_dates[i] for i in time_idx[target_local]]
target_doy = np.array([doy_map(d) for d in target_dates])
print(f"Target doys: {target_doy[0]} to {target_doy[-1]}")

# ===== Hot days =====
thresh_for_target = thresholds_smooth[target_doy - 1]  # (92, 60, 60)
hot = target_sst >= thresh_for_target
hot &= sea_cells[None, :, :]
print(f"Hot days: {hot.sum()} of {hot.size}")

# ===== Per-cell MHWs =====
n_target = len(target_dates)
mhw_mask = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

for ci in range(n_lat):
    for cj in range(n_lon):
        if not sea_cells[ci, cj]:
            continue
        hot_series = hot[:, ci, cj]
        
        hot_idx = np.where(hot_series)[0]
        if len(hot_idx) == 0:
            continue
        
        # Find consecutive runs
        runs = []
        run_start = hot_idx[0]
        run_end = hot_idx[0]
        for i in range(1, len(hot_idx)):
            if hot_idx[i] == hot_idx[i-1] + 1:
                run_end = hot_idx[i]
            else:
                runs.append((run_start, run_end))
                run_start = hot_idx[i]
                run_end = hot_idx[i]
        runs.append((run_start, run_end))
        
        # Keep runs >= 5 days
        long_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        if not long_runs:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined = []
        current = long_runs[0]
        for r in long_runs[1:]:
            gap = r[0] - current[1] - 1
            if 1 <= gap <= 2:
                current = (current[0], r[1])
            else:
                joined.append(current)
                current = r
        joined.append(current)
        
        for s, e in joined:
            mhw_mask[s:e+1, ci, cj] = 1

print(f"MHW mask: {mhw_mask.sum()} cell-days in MHW")

# ===== Regional events =====
active = mhw_mask.any(axis=(1, 2))
print(f"Active days: {active.sum()} of {n_target}")

events = []
if active.any():
    in_run = False
    for i in range(n_target):
        if active[i] and not in_run:
            onset = i
            in_run = True
        elif not active[i] and in_run:
            events.append((onset, i-1))
            in_run = False
    if in_run:
        events.append((onset, n_target-1))

event_list = []
for onset, end in events:
    event_list.append({
        "onset": target_dates[onset].isoformat(),
        "end": target_dates[end].isoformat()
    })

print("Regional events:")
for e in event_list:
    print(f"  {e['onset']} to {e['end']}")

# Print active day dates for verification
active_dates = [target_dates[i].isoformat() for i in range(n_target) if active[i]]
print(f"Active dates (first 10): {active_dates[:10]}")
print(f"Active dates (last 10): {active_dates[-10:] if len(active_dates) > 10 else active_dates}")
print(f"Total active dates: {len(active_dates)}")
