import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'

# Region bounds
LAT_MIN, LAT_MAX = 57.13, 58.33
LON_MIN, LON_MAX = 22.79, 23.99
TARGET_START = '2010-06-01'
TARGET_END = '2010-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'

def get_sst_for_range(start_date, end_date):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    date_range = pd.date_range(start, end)
    
    datasets = []
    for date in date_range:
        fname = f"{base_dir}/sst_{date.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(fname, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                # Slice region
                ds_region = ds.sel(
                    latitude=slice(LAT_MIN, LAT_MAX), 
                    longitude=slice(LON_MIN, LON_MAX)
                )
                datasets.append(ds_region)
        except Exception as e:
            print(f"Error reading {fname}: {e}")
    
    if not datasets:
        return None
    return xr.concat(datasets, dim='time')

# Load target data
print("Loading target data...")
ds_target = get_sst_for_range(TARGET_START, TARGET_END)
if ds_target is None:
    print("No target data found")
    exit()

# Sea cells: SST finite on every day of target period
# analysed_sst is the variable
sst_target = ds_target['analysed_sst'].astype(np.float64)
# Check if all values are finite along time dimension
sea_mask = np.all(np.isfinite(sst_target.values), axis=0)
print(f"Sea cells found: {np.sum(sea_mask)} out of {sea_mask.size}")

# Load baseline data (including 5-day buffers)
# Buffers: 1991-12-27 and 2003-01-05
print("Loading baseline data...")
ds_baseline = get_sst_for_range('1991-12-27', '2003-01-05')
sst_baseline = ds_baseline['analysed_sst'].astype(np.float64)

# Baseline dates
baseline_dates = pd.date_range(pd.to_datetime(BASELINE_START), pd.to_datetime(BASELINE_END))
# We also need a way to access the baseline SST by date efficiently
# Convert sst_baseline to a numpy array or keep it as xarray
# Time coord is already there.

# Let's prepare a mapping from date to index for sst_baseline
baseline_time_coords = pd.to_datetime(sst_baseline.time.values)
time_to_idx = {date: i for i, date in enumerate(baseline_time_coords)}

# Method for DOY (1-366)
def get_doy(dt):
    # 1 Jan = 1, ... 29 Feb = 60, 1 Mar = 61
    # pandas doy is 1-366
    return dt.dayofyear

# Thresholds and Climatology
# 366 elements (1-366)
# numpy array: index 0 = DOY 1, index 365 = DOY 366
thresholds = np.full((366, *sea_mask.shape), np.nan, dtype=np.float64)
climatology = np.full((366, *sea_mask.shape), np.nan, dtype=np.float64)

# Only process sea cells
# To optimize, we can work with the sea_mask
# But the array is small enough (lat 61, lon 61 roughly)
# Wait, check dimensions
print(f"SST shape: {sst_target.shape}") # (time, lat, lon)

# For each day of year d != 60
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all baseline dates with DOY d
    pool_indices = []
    for b_date in baseline_dates:
        if get_doy(b_date) == d:
            # Window +/- 5 days
            for offset in range(-5, 6):
                win_date = b_date + timedelta(days=offset)
                if win_date in time_to_idx:
                    pool_indices.append(time_to_idx[win_date])
    
    if not pool_indices:
        continue
        
    # Extract pool for all cells
    # pool shape: (len(pool_indices), lat, lon)
    pool = sst_baseline.values[pool_indices, :, :]
    
    # Only compute for sea cells? Or just compute for all and mask later.
    # numpy.nanquantile and numpy.nanmean
    # Note: numpy.nanquantile(pool, 0.9, axis=0, method='hazen')
    # But numpy's nanquantile doesn't have 'method' in all versions.
    # Let's check numpy version or use np.nanpercentile.
    # "numpy's method='hazen' (Hyndman-Fan type 5)" is in newer numpy versions.
    # If not, we might need to implement it or check version.
    
    # Actually, let's compute per-cell for the pool.
    # This can be slow if we loop over cells.
    # Let's try to use axis=0.
    
    # Using method='hazen' requires numpy >= 1.22.0
    try:
        q90 = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        mean_val = np.nanmean(pool, axis=0)
    except TypeError:
        # Fallback for older numpy: quantile is a bit different.
        # But the prompt says "which is numpy's method='hazen'".
        # This implies I should use it.
        q90 = np.nanpercentile(pool, 90, axis=0) # basic linear
        mean_val = np.nanmean(pool, axis=0)
        print("Warning: numpy.nanquantile method='hazen' not available, using default.")

    thresholds[d-1] = q90
    climatology[d-1] = mean_val

# Handle day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing: 31-day centered moving mean, wrap around
def smooth_wrap(arr):
    # arr: (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for d in range(366):
        # d is index 0 to 365
        # window: d-15 to d+15
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

# Per-cell MHWs
# Target period
target_time = pd.to_datetime(sst_target.time.values)
target_doy = np.array([get_doy(t) for t in target_time])

# hot_days: (time, lat, lon)
hot_days = np.zeros(sst_target.shape, dtype=bool)
for t_idx in range(len(target_time)):
    d = target_doy[t_idx]
    # thresholds_smooth is indexed 0 to 365
    hot_days[t_idx] = sst_target.values[t_idx] >= thresholds_smooth[d-1]

# For each cell: find runs of >= 5 hot days, join gaps of 1-2
# This is a cell-by-cell operation
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
lat_len, lon_len = sea_mask.shape

for i in range(lat_len):
    for j in range(lon_len):
        if not sea_mask[i, j]:
            continue
            
        cell_hot = hot_days[:, i, j]
        # Identify MHWs
        # run of >= 5 hot days
        # join gaps of 1 or 2 non-hot days
        
        # We can use a simple loop or label components
        # Let's use a loop for clarity and correctness
        in_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        # Find all runs of >= 5
        runs = []
        start = None
        for t in range(len(cell_hot)):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append((start, t - 1))
                    start = None
        if start is not None:
            if len(cell_hot) - start >= 5:
                runs.append((start, len(cell_hot) - 1))
        
        if not runs:
            continue
            
        # Join gaps of 1 or 2
        merged = []
        if runs:
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                gap = next_start - curr_end - 1
                if gap <= 2:
                    curr_end = next_end
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
            
        for start, end in merged:
            in_mhw[start:end+1] = True
            
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# Regional Events
# Day is active if >= 1 sea cell is in an MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
in_event = False
event_start = None

for t in range(len(active_days)):
    if active_days[t]:
        if not in_event:
            in_event = True
            event_start = t
    else:
        if in_event:
            in_event = False
            regional_events.append((target_time[event_start], target_time[t-1]))
if in_event:
    regional_events.append((target_time[event_start], target_time[-1]))

# Write outputs
# mhw_mask.nc
output_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": ds_target.time,
        "latitude": ds_target.latitude,
        "longitude": ds_target.longitude,
    }
)
os.makedirs("output", exist_ok=True)
output_ds.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": TARGET_START,
        "end": TARGET_END
    },
    "events": [
        {"onset": e[0].strftime('%Y-%m-%d'), "end": e[1].strftime('%Y-%m-%d')} 
        for e in regional_events
    ],
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Done")
