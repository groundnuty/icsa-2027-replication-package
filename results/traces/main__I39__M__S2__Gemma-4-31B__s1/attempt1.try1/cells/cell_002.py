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
# Correct coordinate names: latitude, longitude
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# We need SST for the baseline period (extended by 5 days) and target period.
# Baseline extended range: 1991-12-27 to 2003-01-05.
# Target period: 2010-06-01 to 2010-08-31.
# To avoid loading too much, we can slice time.
all_times = ds_region.time.values
all_times_dt = pd.to_datetime(all_times)

# Define ranges
baseline_ext_start = baseline_start - pd.Timedelta(days=5)
baseline_ext_end = baseline_end + pd.Timedelta(days=5)

mask_baseline = (all_times_dt >= baseline_ext_start) & (all_times_dt <= baseline_ext_end)
mask_target = (all_times_dt >= target_start) & (all_times_dt <= target_end)

# Combine masks to get required time indices
mask_needed = mask_baseline | mask_target
ds_needed = ds_region.isel(time=mask_needed).astype('float64')

# Target SST for sea cell identification and MHW detection
sst_target = ds_needed.sst.sel(time=slice(target_start_str, target_end_str))
target_dates = sst_target.time.values

# Sea cells: SST finite on every day of target period
# sst_target shape: (time, latitude, longitude)
sea_mask = np.all(np.isfinite(sst_target.values), axis=0)

# Baseline SST for climatology/threshold
sst_baseline = ds_needed.sst.sel(time=slice(baseline_ext_start_str if 'baseline_ext_start_str' in locals() else '1991-12-27', '2003-01-05'))
# Wait, let's be more precise about the baseline slice.
baseline_dates = pd.date_range(baseline_start, baseline_end)
# The actual data in ds_needed for baseline is everything in [baseline_ext_start, baseline_ext_end].
# Let's just use the boolean mask to get baseline data.
sst_baseline_vals = ds_needed.sst.values[mask_baseline]
baseline_times = all_times_dt[mask_baseline]

# Function to get day of year (1-366) as specified
def get_doy(date):
    # 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61...
    # pd.Timestamp.dayofyear provides exactly this (1-366)
    return date.dayofyear

# Create the pools for each day of year d in [1, 366], d != 60.
#- Baseline dates: 1992-01-01 to 2002-12-31.
#- For each baseline date b with doy(b) == d, pool includes [b-5, b+5].

# Pre-calculate DOY for all baseline_times
baseline_doys = np.array([get_doy(t) for t in baseline_times])

# To optimize, we can find indices for each baseline date that has DOY d
# and then expand to ±5 days.
# However, it's simpler to:
# For each d in 1..366 (d!=60):
#   Find dates in [1992-01-01, 2002-12-31] with doy == d.
#   For each such date, get indices of all dates in [baseline_times] within ±5 days.
#   Union those indices.

# First, find indices of dates in the range [1992-01-01, 2002-12-31]
baseline_range_mask = (baseline_times >= baseline_start) & (baseline_times <= baseline_end)
baseline_range_indices = np.where(baseline_range_mask)[0]
baseline_range_times = baseline_times[baseline_range_mask]
baseline_range_doys = baseline_doys[baseline_range_mask]

thresholds = np.full((366, sst_baseline_vals.shape[1], sst_baseline_vals.shape[2]), np.nan)
climatology = np.full((366, sst_baseline_vals.shape[1], sst_baseline_vals.shape[2]), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Dates in [1992-01-01, 2002-12-31] with DOY d
    dates_with_doy_d = baseline_range_times[baseline_range_doys == d]
    
    if len(dates_with_doy_d) == 0:
        continue
    
    # Find all indices in baseline_times that are within ±5 days of any date in dates_with_doy_d
    pool_indices = set()
    for date in dates_with_doy_d:
        # Find window [date - 5, date + 5]
        # Since baseline_times is sorted and daily (mostly), we can find the window.
        # Actually, let's just use the times.
        win_start = date - pd.Timedelta(days=5)
        win_end = date + pd.Timedelta(days=5)
        
        # Find indices in baseline_times
        idx_start = np.searchsorted(baseline_times, win_start)
        idx_end = np.searchsorted(baseline_times, win_end, side='right')
        for i in range(idx_start, idx_end):
            pool_indices.add(i)
            
    pool_vals = sst_baseline_vals[list(pool_indices), :, :]
    
    # Threshold: 90th percentile, method="hazen" (Type 5)
    # numpy.quantile method="hazen" is available in numpy 1.22.0+
    # If not available, we might need another way.
    # Let's check numpy version.
    import numpy as np
    # We'll use np.nanquantile(pool_vals, 0.9, axis=0, method='hazen')
    thresholds[d-1] = np.nanquantile(pool_vals, 0.9, axis=0, method='hazen')
    climatology[d-1] = np.nanmean(pool_vals, axis=0)

# Handle day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing: 31-day centered moving mean, wrap around
def smooth(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # window: d-15 to d+15 (modulo 366)
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices]
        # Compute mean over the first axis (the time window), ignoring NaNs
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smooth = smooth(thresholds)
climatology_smooth = smooth(climatology)

# Target Period Analysis
# SST for target period: sst_target (time, lat, lon)
target_doys = np.array([get_doy(t) for t in target_dates])
# threshold for these days: thresholds_smooth[target_doys - 1]
thresh_target = thresholds_smooth[target_doys - 1]

# Hot days: SST >= threshold
hot_days = (sst_target.values >= thresh_target).astype(np.uint8)

# Per-cell MHW detection
# hot_days: (time, lat, lon)
# We need to process per cell.
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
        # Join gaps of 1 or 2 non-hot days
        
        # Initial run detection
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
        if runs:
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

# Regional events
# Day is active if at least one sea cell is in an MHW
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
                "onset": target_dates[start].strftime('%Y-%m-%d'),
                "end": target_dates[d-1].strftime('%Y-%m-%d')
            })
            start = None
if start is not None:
    regional_events.append({
        "onset": target_dates[start].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    })

# Write output files
os.makedirs('output', exist_ok=True)

# mhw_mask.nc
# Need to use the original coordinates for the target period.
mhw_ds = xr.Dataset(
    {"mhw": (["time", "latitude", "longitude"], mhw_mask.astype(np.uint8))},
    coords={
        "time": target_dates,
        "latitude": ds_region.latitude.values,
        "longitude": ds_region.longitude.values,
    },
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start.strftime('%Y-%m-%d'), "end": baseline_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Analysis complete. Files written.")
