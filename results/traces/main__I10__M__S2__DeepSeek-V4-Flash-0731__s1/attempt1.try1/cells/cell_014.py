
import numpy as np
from datetime import date, timedelta
from collections import defaultdict
import xarray as xr
import pandas as pd
import json
import os

# ===== Load data =====
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat = ds['latitude'].values
lon = ds['longitude'].values
time = ds['time'].values
time_dates = pd.to_datetime(time).date

lat_mask = (lat >= 55.67) & (lat <= 56.87)
lon_mask = (lon >= 16.45) & (lon <= 17.65)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

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

# ===== Sea cells =====
target_sst = sst[target_local]
sea_cells = np.all(np.isfinite(target_sst), axis=0)

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
pool_sst = sst[pool_local]  # (4028, 60, 60)

thresholds = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

# Vectorized mean (climatology) and percentile per cell
for d in range(1, n_doy + 1):
    if d == 60:
        continue
    idx = doy_to_pool_idx_arr[d]
    if len(idx) == 0:
        continue
    pool_data = pool_sst[idx]  # (n_pool, n_lat, n_lon)
    
    # Mask sea cells and finite values
    valid = np.isfinite(pool_data) & sea_cells[None, :, :]
    counts = valid.sum(axis=0)
    
    # Climatology (mean)
    sums = np.where(valid, pool_data, 0.0).sum(axis=0)
    climatology[d-1] = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
    
    # Threshold (90th percentile, hazen) - vectorized per cell
    # We need to handle each cell separately since percentile is not vectorizable easily
    # Use a loop over cells but only for sea cells
    valid_cells = sea_cells & (counts > 0)
    for ci in range(n_lat):
        for cj in range(n_lon):
            if valid_cells[ci, cj]:
                vals = pool_data[:, ci, cj]
                vals_valid = vals[valid[:, ci, cj]]
                thresholds[d-1, ci, cj] = np.percentile(vals_valid, 90, method='hazen')

print("Computed thresholds and climatology")

# Set day 60 = mean of days 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# ===== Smoothing (31-day centered moving average, wraps around) =====
def smooth_wrap(arr):
    """arr: (366, n_lat, n_lon) - smooth along axis 0 with 31-day centered MA wrapping."""
    n = 366
    result = np.zeros_like(arr)
    for d in range(n):
        indices = [(d + k) % n for k in range(-15, 16)]
        result[d] = np.nanmean(arr[indices], axis=0)
    return result

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

print("Smoothed thresholds and climatology")

# ===== Per-cell MHWs =====
target_dates = [time_dates[i] for i in time_idx[target_local]]
target_doy = np.array([doy_map(d) for d in target_dates])
print("Target doys:", target_doy[0], "to", target_doy[-1])

# For each target day, threshold and climatology (already smoothed)
# sst target: (92, 60, 60)
# thresholds_smooth[target_doy-1]: (92, 60, 60)
thresh_for_target = thresholds_smooth[target_doy - 1]
clim_for_target = climatology_smooth[target_doy - 1]

# Hot days: SST >= threshold
hot = target_sst >= thresh_for_target
# Also mask sea cells
hot &= sea_cells[None, :, :]

print("Hot days per cell:", hot.sum(axis=0).sum(), "of", hot.size)

# Find per-cell MHWs
# For each sea cell, find runs of >=5 consecutive hot days, then join gaps of 1-2 days
n_target = len(target_dates)

# Precompute per-cell MHW membership
# mhw_mask: (n_target, n_lat, n_lon) - 1 if cell is inside a per-cell MHW on that day
mhw_mask = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

for ci in range(n_lat):
    for cj in range(n_lon):
        if not sea_cells[ci, cj]:
            continue
        hot_series = hot[:, ci, cj].astype(np.int8)
        
        # Find runs of hot days
        # Find indices where hot is True
        hot_idx = np.where(hot_series == 1)[0]
        if len(hot_idx) == 0:
            continue
        
        # Group consecutive hot days
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
        
        # Keep runs of length >= 5
        long_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        if not long_runs:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
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
        
        # Mark MHW days
        for s, e in joined:
            mhw_mask[s:e+1, ci, cj] = 1

print("MHW mask sum:", mhw_mask.sum())

# ===== Regional events =====
# A day is active if at least one sea cell is inside a per-cell MHW
active = mhw_mask.any(axis=(1, 2))  # (n_target,)

# Find maximal runs of active days
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

# Convert to dates
event_list = []
for onset, end in events:
    event_list.append({
        "onset": target_dates[onset].isoformat(),
        "end": target_dates[end].isoformat()
    })

print("Regional events:", event_list)

# ===== Write output files =====
os.makedirs("output", exist_ok=True)

# Write mhw_mask.nc
# Need time, lat, lon coordinates
target_time = ds['time'].values[time_idx[target_local]]
region_lat = ds['latitude'].values[lat_idx]
region_lon = ds['longitude'].values[lon_idx]

ds_out = xr.Dataset(
    {
        "mhw": (("time", "lat", "lon"), mhw_mask)
    },
    coords={
        "time": target_time,
        "lat": region_lat,
        "lon": region_lon,
    }
)
ds_out.to_netcdf("output/mhw_mask.nc", engine="h5netcdf")

# Write report.json
report = {
    "region": {
        "lat_min": 55.67,
        "lat_max": 56.87,
        "lon_min": 16.45,
        "lon_max": 17.65
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2005-06-01",
        "end": "2005-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Done writing outputs")
print("Events:", event_list)
