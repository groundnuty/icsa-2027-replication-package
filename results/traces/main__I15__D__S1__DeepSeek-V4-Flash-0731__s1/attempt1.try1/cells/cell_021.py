
import xarray as xr
import numpy as np
import datetime
import pandas as pd
import json
import os

def date_to_doy(dt):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:dt.month-1]) + dt.day
    return doy

def smooth_circular(arr):
    """Smooth a 366-element array with unweighted centred 31-day moving average wrapping around."""
    n = 366
    padded = np.concatenate([arr[-15:], arr, arr[:15]])
    result = np.zeros(n)
    for i in range(n):
        result[i] = np.mean(padded[i:i+31])
    return result

# ============ Load data ============
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
time_vals = ds.time.values

lat_idx = np.where((lat >= 56.13) & (lat <= 57.33))[0]
lon_idx = np.where((lon >= 17.71) & (lon <= 18.91))[0]

region_lat = lat[lat_idx]
region_lon = lon[lon_idx]

# Target period
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
target_mask = (time_vals >= target_start) & (time_vals <= target_end)
target_time_idx = np.where(target_mask)[0]
target_dates = [pd.Timestamp(t).date() for t in time_vals[target_time_idx]]

# Baseline period
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time_vals >= baseline_start) & (time_vals <= baseline_end)
baseline_time_idx = np.where(baseline_mask)[0]
baseline_dates = [pd.Timestamp(t).date() for t in time_vals[baseline_time_idx]]

# Extract data
baseline_sst = ds.analysed_sst[baseline_time_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)
target_sst = ds.analysed_sst[target_time_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)

# Identify sea cells
sea_mask = np.all(np.isfinite(target_sst), axis=0)
sea_y, sea_x = np.where(sea_mask)
print(f"Sea cells: {len(sea_y)}")

# ============ Build pools ============
date_to_idx = {dt: i for i, dt in enumerate(baseline_dates)}

pools_idx = {}
for d_val in range(1, 367):
    if d_val == 60:
        continue
    bdt_with_doy = []
    for dt in baseline_dates:
        if datetime.date(1992,1,1) <= dt <= datetime.date(2002,12,31) and date_to_doy(dt) == d_val:
            bdt_with_doy.append(dt)
    pool_idx_set = set()
    for bdt in bdt_with_doy:
        for i in range(-5, 6):
            dt2 = bdt + datetime.timedelta(days=i)
            if dt2 in date_to_idx:
                pool_idx_set.add(date_to_idx[dt2])
    pools_idx[d_val] = sorted(pool_idx_set)

# ============ Compute threshold and climatology ============
threshold = np.full((366, 60, 60), np.nan, dtype=np.float64)
climatology = np.full((366, 60, 60), np.nan, dtype=np.float64)

for d_val in range(1, 367):
    if d_val == 60:
        continue
    pool_idx = pools_idx[d_val]
    pool_data = baseline_sst[pool_idx]
    for ci in range(len(sea_y)):
        y, x = sea_y[ci], sea_x[ci]
        vals = pool_data[:, y, x]
        finite_vals = vals[np.isfinite(vals)]
        if len(finite_vals) > 0:
            threshold[d_val-1, y, x] = np.quantile(finite_vals, 0.9, method='hazen')
            climatology[d_val-1, y, x] = np.mean(finite_vals)

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# ============ Smooth ============
smooth_threshold = np.zeros_like(threshold)
smooth_climatology = np.zeros_like(climatology)
for ci in range(len(sea_y)):
    y, x = sea_y[ci], sea_x[ci]
    smooth_threshold[:, y, x] = smooth_circular(threshold[:, y, x])
    smooth_climatology[:, y, x] = smooth_circular(climatology[:, y, x])

print("Threshold and climatology computed and smoothed")

# ============ Per-cell MHWs ============
# Target doys
target_doys = [date_to_doy(dt) for dt in target_dates]

# Hot days: SST >= threshold for that doy
hot = np.zeros_like(target_sst, dtype=bool)  # (92, 60, 60)
for t_idx, doy in enumerate(target_doys):
    for ci in range(len(sea_y)):
        y, x = sea_y[ci], sea_x[ci]
        if np.isfinite(target_sst[t_idx, y, x]):
            hot[t_idx, y, x] = target_sst[t_idx, y, x] >= smooth_threshold[doy-1, y, x]

# Find per-cell MHWs: runs of >=5 consecutive hot days, with gaps of 1-2 joined
# mhw_mask: (92, 60, 60) - 1 if cell is inside a per-cell MHW on that day
mhw_mask = np.zeros((92, 60, 60), dtype=np.uint8)

for ci in range(len(sea_y)):
    y, x = sea_y[ci], sea_x[ci]
    hot_series = hot[:, y, x]
    
    # Find runs of hot days
    # First identify runs of >= 5 consecutive hot days
    # Then join runs separated by 1-2 non-hot days
    
    # Find all hot runs
    runs = []
    i = 0
    n = len(hot_series)
    while i < n:
        if hot_series[i]:
            j = i
            while j < n and hot_series[j]:
                j += 1
            runs.append((i, j-1))  # inclusive start, end
            i = j
        else:
            i += 1
    
    # Filter runs of >= 5 days
    valid_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    # Join runs separated by 1-2 non-hot days
    if valid_runs:
        joined = [valid_runs[0]]
        for s, e in valid_runs[1:]:
            prev_s, prev_e = joined[-1]
            gap = s - prev_e - 1
            if gap <= 2:
                joined[-1] = (prev_s, e)
            else:
                joined.append((s, e))
        
        # Mark the MHW mask
        for s, e in joined:
            mhw_mask[s:e+1, y, x] = 1

print("Per-cell MHWs computed")

# ============ Regional events ============
# A day is active if at least one sea cell is inside a per-cell MHW
active = np.any(mhw_mask > 0, axis=(1, 2))  # (92,)

# Regional MHW events: maximal runs of consecutive active days
events = []
i = 0
n = len(active)
while i < n:
    if active[i]:
        j = i
        while j < n and active[j]:
            j += 1
        events.append((i, j-1))
        i = j
    else:
        i += 1

print("Regional events:", len(events))
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]}")

# Build report
event_list = [{"onset": str(target_dates[s]), "end": str(target_dates[e])} for s, e in events]

report = {
    "region": {
        "lat_min": 56.13,
        "lat_max": 57.33,
        "lon_min": 17.71,
        "lon_max": 18.91
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": str(target_dates[0]),
        "end": str(target_dates[-1])
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

print(json.dumps(report, indent=2))
