import xarray as xr
import numpy as np
import pandas as pd
import json
import fsspec
import os
from datetime import datetime, timedelta

# Parameters
lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45
target_start_str = '2014-06-01'
target_end_str = '2014-08-31'
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'
expanded_start_str = '1991-12-27'
expanded_end_str = '2003-01-05'

# File paths
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

# Create output directory
os.makedirs('output', exist_ok=True)

# Initialize filesystem and download
fs = fsspec.filesystem('onedata')
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine="h5netcdf")
sst_var = 'analysed_sst'

# Slice region
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Target period SST
ds_target = ds_reg.sel(time=slice(target_start_str, target_end_str))
target_times = ds_target.time.values

# Sea cells: SST finite on every day of the target period
sst_target = ds_target[sst_var].values.astype(np.float64)
is_finite = np.all(np.isfinite(sst_target), axis=0)

# Expanded baseline SST
ds_baseline_exp = ds_reg.sel(time=slice(expanded_start_str, expanded_end_str))
sst_baseline = ds_baseline_exp[sst_var].values.astype(np.float64)
baseline_times = pd.to_datetime(ds_baseline_exp.time.values)

def get_day_of_year(dt):
    return dt.day_of_year

baseline_doy = np.array([get_day_of_year(t) for t in baseline_times])

# Thresholds and Climatology
n_lat = sst_target.shape[1]
n_lon = sst_target.shape[2]
thresholds = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
climatology = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)

# For each day of year d other than 60
baseline_start_ts = pd.Timestamp(baseline_start_str)
baseline_end_ts = pd.Timestamp(baseline_end_str)

for d in range(1, 367):
    if d == 60:
        continue
    
    baseline_mask = (baseline_times >= baseline_start_ts) & (baseline_times <= baseline_end_ts)
    baseline_doy_mask = (baseline_doy == d) & baseline_mask
    target_baseline_dates = baseline_times[baseline_doy_mask]
    
    if len(target_baseline_dates) == 0:
        continue

    pool_indices = []
    for b_date in target_baseline_dates:
        win_start = b_date - pd.Timedelta(days=5)
        win_end = b_date + pd.Timedelta(days=5)
        idx_start = np.searchsorted(baseline_times, win_start)
        idx_end = np.searchsorted(baseline_times, win_end, side='right')
        pool_indices.extend(range(idx_start, idx_end))
    
    unique_indices = np.unique(pool_indices)
    pool_sst = sst_baseline[unique_indices, :, :]
    
    thresholds[:, :, d-1] = np.nanpercentile(pool_sst, 90, axis=0, method='hazen')
    climatology[:, :, d-1] = np.nanmean(pool_sst, axis=0)

# Day 60: mean of 59 and 61
thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
climatology[:, :, 59] = (climatology[:, :, 58] + climatology[:, :, 60]) / 2

# Smoothing: 31-day moving mean, wrapping
def smooth_366(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        indices = np.arange(d - 15, d + 16) % 366
        window_data = arr[:, :, indices]
        smoothed[:, :, d] = np.nanmean(window_data, axis=2)
    return smoothed

thresholds_smoothed = smooth_366(thresholds)
climatology_smoothed = smooth_366(climatology)

# Target period analysis
target_doy = np.array([pd.to_datetime(t).day_of_year for t in target_times])
thresh_target = np.transpose(thresholds_smoothed[:, :, target_doy - 1], (2, 0, 1))

is_hot = (sst_target >= thresh_target)
mhw_mask = np.zeros_like(is_hot, dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not is_finite[i, j]:
            continue
        
        cell_hot = is_hot[:, i, j]
        n_days = len(cell_hot)
        in_mhw = np.zeros(n_days, dtype=bool)
        
        hot_runs = []
        start = None
        for t in range(n_days):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        hot_runs.append((start, t - 1))
                    start = None
        if start is not None and n_days - start >= 5:
            hot_runs.append((start, n_days - 1))
        
        if not hot_runs:
            continue
            
        merged = True
        while merged:
            merged = False
            new_runs = []
            if not hot_runs:
                break
            hot_runs.sort()
            curr_start, curr_end = hot_runs[0]
            for next_start, next_end in hot_runs[1:]:
                gap = next_start - curr_end - 1
                if gap <= 2:
                    curr_end = next_end
                    merged = True
                else:
                    new_runs.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            new_runs.append((curr_start, curr_end))
            hot_runs = new_runs
            
        for start, end in hot_runs:
            in_mhw[start : end + 1] = True
        
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for t in range(len(active_days)):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((target_times[start], target_times[t-1]))
            start = None
if start is not None:
    regional_events.append((target_times[start], target_times[-1]))

# Prepare output files
ds_mhw = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_times,
        "latitude": ds_reg.latitude.values,
        "longitude": ds_reg.longitude.values,
    },
)
ds_mhw.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {
        "lat_min": float(lat_min),
        "lat_max": float(lat_max),
        "lon_min": float(lon_min),
        "lon_max": float(lon_max),
    },
    "baseline_analysed": {
        "start": baseline_start_str,
        "end": baseline_end_str,
    },
    "target_analysed": {
        "start": target_start_str,
        "end": target_end_str,
    },
    "events": [
        {"onset": pd.to_datetime(e[0]).strftime('%Y-%m-%d'), "end": pd.to_datetime(e[1]).strftime('%Y-%m-%d')}
        for e in regional_events
    ],
    "complete": True,
    "caveats": "",
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Analysis complete.")
