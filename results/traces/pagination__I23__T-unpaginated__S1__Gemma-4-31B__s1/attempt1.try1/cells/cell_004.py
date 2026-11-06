import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

# Spatial bounds
lat_min, lat_max = 57.41, 58.61
lon_min, lon_max = 18.69, 19.89
target_start_str = '2013-06-01'
target_end_str = '2013-08-31'
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'

target_start = pd.to_datetime(target_start_str)
target_end = pd.to_datetime(target_end_str)
baseline_start = pd.to_datetime(baseline_start_str)
baseline_end = pd.to_datetime(baseline_end_str)
pool_start = baseline_start - pd.Timedelta(days=5)
pool_end = baseline_end + pd.Timedelta(days=5)

all_files = fs.ls(base_path)
target_files = sorted([f for f in all_files if target_start <= pd.to_datetime(f.split('_')[-1].replace('.nc', '')) <= target_end])
baseline_files = sorted([f for f in all_files if pool_start <= pd.to_datetime(f.split('_')[-1].replace('.nc', '')) <= pool_end])

# Helper to load SST for a set of files
def load_sst_region(files):
    sst_data = []
    dates = []
    lats, lons = None, None
    for f in files:
        date_str = f.split('_')[-1].replace('.nc', '')
        dates.append(pd.to_datetime(date_str))
        with fs.open(f, "rb") as f_obj:
            ds = xr.open_dataset(f_obj, engine="h5netcdf")
            ds_sub = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            if lats is None:
                lats = ds_sub.latitude.values
                lons = ds_sub.longitude.values
            sst_data.append(ds_sub.analysed_sst.values.astype(np.float64))
    return np.array(sst_data), np.array(dates), lats, lons

# Load Target SST
target_sst, target_dates, lats, lons = load_sst_region(target_files)
# target_sst shape: (time, lat, lon)
n_time_target, n_lat, n_lon = target_sst.shape

# 1. Find sea cells
# Finite on every day of the target period
sea_mask = np.isfinite(target_sst).all(axis=0)

# Load Baseline SST
baseline_sst, baseline_dates, _, _ = load_sst_region(baseline_files)
# baseline_sst shape: (time, lat, lon)

# Pre-calculate DOY for baseline dates
baseline_doys = np.array([d.dayofyear for d in baseline_dates])

# 2. Compute Threshold and Climatology
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

# Baseline dates for the core 1992-2002 period
baseline_range_dates = pd.date_range(baseline_start, baseline_end)
baseline_date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

for d in range(1, 367):
    if d == 60:
        continue
    
    # Pool consists of SST values whose date lies within +/- 5 days 
    # of a baseline date (1992-01-01 to 2002-12-31) whose DOY is d.
    pool_indices = []
    for T in baseline_range_dates:
        if T.dayofyear == d:
            for delta in range(-5, 6):
                date_win = T + pd.Timedelta(days=delta)
                if date_win in baseline_date_to_idx:
                    pool_indices.append(baseline_date_to_idx[date_win])
    
    if not pool_indices:
        continue
    
    pool_vals = baseline_sst[pool_indices] # (N, lat, lon)
    
    # Quantile and mean along the time axis (0)
    # np.nanquantile is used to ignore NaNs.
    # method='hazen' is Hyndman-Fan type 5 (MATLAB default)
    thresholds[d-1] = np.nanquantile(pool_vals, 0.9, axis=0, method='hazen')
    climatologies[d-1] = np.nanmean(pool_vals, axis=0)

# Day 60 logic
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day moving mean, wrap around
def smooth_31(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d] = np.nanmean(arr[indices], axis=0)
    return smoothed

thresholds = smooth_31(thresholds)
climatologies = smooth_31(climatologies)

# 3. Per-cell MHWs
target_doys = np.array([d.dayofyear for d in target_dates])
hot_mask = np.zeros(target_sst.shape, dtype=bool)
for t in range(n_time_target):
    doy = target_doys[t]
    hot_mask[t] = target_sst[t] >= thresholds[doy-1]

mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        
        cell_hot = hot_mask[:, i, j]
        
        # Identify hot runs of >= 5 days
        is_mhw = np.zeros(n_time_target, dtype=bool)
        runs = []
        start = None
        for t in range(n_time_target):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append([start, t-1])
                    start = None
        if start is not None and n_time_target - start >= 5:
            runs.append([start, n_time_target-1])
        
        if not runs:
            continue
        
        # Join gaps of 1 or 2 non-hot days
        merged = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            if next_start - curr_end - 1 <= 2:
                curr_end = next_end
            else:
                merged.append([curr_start, curr_end])
                curr_start, curr_end = next_start, next_end
        merged.append([curr_start, curr_end])
        
        for start, end in merged:
            mhw_mask[start:end+1, i, j] = 1

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for t in range(n_time_target):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append({
                "onset": target_dates[start].strftime('%Y-%m-%d'),
                "end": target_dates[t-1].strftime('%Y-%m-%d')
            })
            start = None
if start is not None:
    regional_events.append({
        "onset": target_dates[start].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    })

# Output
os.makedirs('output', exist_ok=True)
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_dates, "latitude": lats, "longitude": lons}
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": baseline_dates[0].strftime('%Y-%m-%d'),
        "end": baseline_dates[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_dates[0].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Analysis completed successfully.")
