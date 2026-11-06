import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# File path
dataset_path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Region and time
lat_min, lat_max = 60.49, 61.69
lon_min, lon_max = 17.25, 18.45
target_start_str = '2010-06-01'
target_end_str = '2010-08-31'
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'

target_start = pd.to_datetime(target_start_str)
target_end = pd.to_datetime(target_end_str)
baseline_start = pd.to_datetime(baseline_start_str)
baseline_end = pd.to_datetime(baseline_end_str)

# Load dataset
ds = xr.open_dataset(dataset_path, engine="h5netcdf")
# Subset the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Time range needed
# Baseline extended: [1991-12-27, 2003-01-05]
# Target: [2010-06-01, 2010-08-31]
baseline_ext_start = baseline_start - pd.Timedelta(days=5)
baseline_ext_end = baseline_end + pd.Timedelta(days=5)

# Get all times in the dataset
all_times = pd.to_datetime(ds_region.time.values)

# Mask for baseline and target
mask_baseline_ext = (all_times >= baseline_ext_start) & (all_times <= baseline_ext_end)
mask_target = (all_times >= target_start) & (all_times <= target_end)
mask_needed = mask_baseline_ext | mask_target

# Subset time and cast to float64
ds_needed = ds_region.isel(time=mask_needed).astype('float64')
sst_needed = ds_needed.analysed_sst.values
times_needed = all_times[mask_needed]

# Separate baseline and target data
# Baseline extended data for pool calculation
# We need a way to map times_needed to their corresponding baseline values
# Let's find the indices of baseline_ext and target
baseline_ext_indices = np.where(mask_baseline_ext)[0] # Indices in all_times
# Wait, ds_needed is already sliced. Let's find indices within ds_needed.
# mask_baseline_ext is on all_times.
# We need indices of all_times that are in [baseline_ext_start, baseline_ext_end] AND are in mask_needed.
# Since mask_needed = mask_baseline_ext | mask_target, 
# any index in mask_baseline_ext is also in mask_needed.
# But we need the indices *relative to ds_needed*.

# Let's just use the boolean arrays on times_needed.
baseline_ext_mask = (times_needed >= baseline_ext_start) & (times_needed <= baseline_ext_end)
target_mask = (times_needed >= target_start) & (times_needed <= target_end)

sst_baseline_ext = sst_needed[baseline_ext_mask]
times_baseline_ext = times_needed[baseline_ext_mask]

sst_target = sst_needed[target_mask]
times_target = times_needed[target_mask]

# 1. Sea cells: SST finite on every day of target period
# sst_target shape: (time, lat, lon)
sea_mask = np.all(np.isfinite(sst_target), axis=0)

# 2. Threshold and Climatology
# Baseline range: 1992-01-01 to 2002-12-31
baseline_range_mask = (times_baseline_ext >= baseline_start) & (times_baseline_ext <= baseline_end)
baseline_range_times = times_baseline_ext[baseline_range_mask]
baseline_range_indices = np.where(baseline_range_mask)[0]

# We need the pool for each d in 1..366 (d!=60)
thresholds = np.full((366, sst_baseline_ext.shape[1], sst_baseline_ext.shape[2]), np.nan)
climatology = np.full((366, sst_baseline_ext.shape[1], sst_baseline_ext.shape[2]), np.nan)

# To speed up, pre-calculate DOY for all times_baseline_ext
baseline_ext_doys = np.array([t.dayofyear for t in times_baseline_ext])

for d in range(1, 367):
    if d == 60:
        continue
    
    # Dates in [1992-01-01, 2002-12-31] with DOY d
    # Find these dates in times_baseline_ext
    doy_d_indices = baseline_range_indices[baseline_ext_doys[baseline_range_indices] == d]
    
    if len(doy_d_indices) == 0:
        continue
        
    # For each such date, pool includes ±5 days.
    # Since times_baseline_ext is daily and sorted, we can find the range.
    # Actually, a simpler way:
    # Any date in times_baseline_ext that is within 5 days of ANY date in doy_d_indices.
    
    # Use a boolean mask for the pool on times_baseline_ext
    pool_mask = np.zeros(len(times_baseline_ext), dtype=bool)
    for idx in doy_d_indices:
        date = times_baseline_ext[idx]
        win_start = date - pd.Timedelta(days=5)
        win_end = date + pd.Timedelta(days=5)
        
        # Find indices in times_baseline_ext
        idx_start = np.searchsorted(times_baseline_ext, win_start)
        idx_end = np.searchsorted(times_baseline_ext, win_end, side='right')
        pool_mask[idx_start:idx_end] = True
    
    pool_vals = sst_baseline_ext[pool_mask]
    
    # Threshold: 90th percentile, method="hazen"
    thresholds[d-1] = np.nanquantile(pool_vals, 0.9, axis=0, method='hazen')
    climatology[d-1] = np.nanmean(pool_vals, axis=0)

# Day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing: 31-day centred moving mean
def smooth(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smooth = smooth(thresholds)
climatology_smooth = smooth(climatology)

# 3. Per-cell MHWs over target period
target_doys = np.array([t.dayofyear for t in times_target])
thresh_target = thresholds_smooth[target_doys - 1]

# Hot days: SST >= threshold
hot_days = (sst_target >= thresh_target).astype(np.uint8)

# Per-cell processing
lat_size, lon_size = sea_mask.shape
mhw_mask = np.zeros_like(hot_days, dtype=np.uint8)

for i in range(lat_size):
    for j in range(lon_size):
        if not sea_mask[i, j]:
            continue
        
        cell_hot = hot_days[:, i, j]
        n_days = len(cell_hot)
        cell_mhw = np.zeros(n_days, dtype=np.uint8)
        
        # Find runs of >= 5 hot days
        runs = []
        start = None
        for d in range(n_days):
            if cell_hot[d] == 1:
                if start is None:
                    start = d
            else:
                if start is not None:
                    if d - start >= 5:
                        runs.append([start, d - 1])
                    start = None
        if start is not None:
            if n_days - start >= 5:
                runs.append([start, n_days - 1])
        
        if not runs:
            continue
            
        # Join gaps of 1 or 2 non-hot days
        merged_runs = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            gap = next_start - curr_end - 1
            if gap <= 2:
                curr_end = next_end
            else:
                merged_runs.append([curr_start, curr_end])
                curr_start, curr_end = next_start, next_end
        merged_runs.append([curr_start, curr_end])
            
        for start, end in merged_runs:
            cell_mhw[start : end + 1] = 1
            
        mhw_mask[:, i, j] = cell_mhw

# 4. Regional events
active_days = np.any(mhw_mask, axis=(1, 2))

regional_events = []
start = None
for d in range(len(active_days)):
    if active_days[d]:
        if start is None:
            start = d
    else:
        if start is not None:
            regional_events.append({
                "onset": times_target[start].strftime('%Y-%m-%d'),
                "end": times_target[d-1].strftime('%Y-%m-%d')
            })
            start = None
if start is not None:
    regional_events.append({
        "onset": times_target[start].strftime('%Y-%m-%d'),
        "end": times_target[-1].strftime('%Y-%m-%d')
    })

# Results
os.makedirs('output', exist_ok=True)

# mhw_mask.nc
mhw_ds = xr.Dataset(
    {"mhw": (["time", "latitude", "longitude"], mhw_mask.astype(np.uint8))},
    coords={
        "time": times_target,
        "latitude": ds_region.latitude.values,
        "longitude": ds_region.longitude.values,
    },
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": times_baseline_ext[0].strftime('%Y-%m-%d'), 
        "end": times_baseline_ext[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": times_target[0].strftime('%Y-%m-%d'), 
        "end": times_target[-1].strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Analysis complete.")
