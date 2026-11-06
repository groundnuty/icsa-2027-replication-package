import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

# Constants
LAT_MIN, LAT_MAX = 57.83, 59.03
LON_MIN, LON_MAX = 17.41, 18.61
TARGET_START = '2007-06-01'
TARGET_END = '2007-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'
BASELINE_LOAD_START = '1991-12-27'
BASELINE_LOAD_END = '2003-01-05'

def get_doy(dt):
    """
    1 January = 1, ..., 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366.
    """
    # Using pandas Timestamps for easier handling
    ts = pd.Timestamp(dt)
    # pandas .dayofyear is 1-366. 
    # In leap year, 29 Feb is 60.
    # In non-leap year, 1 Mar is 60.
    # The task specifies: 28 Feb = 59, 29 Feb = 60, 1 Mar = 61.
    # This means for non-leap years, we need to shift everything from March onwards by 1.
    
    year = ts.year
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    doy = ts.dayofyear
    
    if not is_leap and doy >= 60:
        doy += 1
    return doy

# Open dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine="h5netcdf")
ds_region = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))

# Target period SST
sst_target_ds = ds_region.analysed_sst.sel(time=slice(TARGET_START, TARGET_END))
time_target = sst_target_ds.time.values
sst_target = sst_target_ds.values.astype(np.float64)

# Baseline period SST (including windows)
sst_baseline_ds = ds_region.analysed_sst.sel(time=slice(BASELINE_LOAD_START, BASELINE_LOAD_END))
time_baseline_load = sst_baseline_ds.time.values
sst_baseline_load = sst_baseline_ds.values.astype(np.float64)

# 1. Sea cells: SST is finite on every day of the target period
# sst_target shape: (time, lat, lon)
finite_mask = np.all(np.isfinite(sst_target), axis=0)
sea_cells = finite_mask

# 2. Threshold and Climatology
# Setup baseline dates and their DOYs
baseline_dates = pd.date_range(BASELINE_START, BASELINE_END)
doy_to_dates = {d: [] for d in range(1, 367)}
for dt in baseline_dates:
    d = get_doy(dt)
    if d != 60:
        doy_to_dates[d].append(dt)

# Map baseline load dates to their index for fast lookup
date_to_idx = {np.datetime64(dt): i for i, dt in enumerate(time_baseline_load)}

# Initialize arrays for threshold and climatology
# Shape: (doy, lat, lon)
thresholds = np.full((367, *sst_target.shape[1:]), np.nan, dtype=np.float64)
climatologies = np.full((367, *sst_target.shape[1:]), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find the pool of dates: union of [T-5, T+5] for all baseline dates T with DOY d
    pool_dates = set()
    for T in doy_to_dates[d]:
        for offset in range(-5, 6):
            pool_dates.add(T + timedelta(days=offset))
    
    # Get the SST values for these dates
    pool_values = []
    for p_date in pool_dates:
        p_date_np = np.datetime64(p_date)
        if p_date_np in date_to_idx:
            pool_values.append(sst_baseline_load[date_to_idx[p_date_np]])
    
    if pool_values:
        pool_arr = np.stack(pool_values, axis=0) # (num_dates, lat, lon)
        # Threshold: 90th percentile (numpy method="hazen")
        thresholds[d] = np.nanpercentile(pool_arr, 90, axis=0, method="hazen")
        # Climatology: mean
        climatologies[d] = np.nanmean(pool_arr, axis=0)

# Set day 60 to the mean of days 59 and 61
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatologies[60] = (climatologies[59] + climatologies[61]) / 2

# Smooth each of them (31-day moving mean, wrapped)
def smooth_366(arr):
    # arr is (367, lat, lon), but we use index 1 to 366
    smoothed = np.full_like(arr, np.nan)
    data = arr[1:] # index 0 to 365 (corresponding to doy 1 to 366)
    
    # For each d in 0...365: average d-15...d+15 mod 366
    for d in range(366):
        window_indices = [(d + i) % 366 for i in range(-15, 16)]
        window_data = data[window_indices]
        smoothed[d+1] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatologies = smooth_366(climatologies)

# 3. Per-cell MHWs
# Target period
doy_target = np.array([get_doy(t) for t in time_target])
# sst_target: (time, lat, lon)
# thresholds: (367, lat, lon)
hot_mask = np.zeros(sst_target.shape, dtype=bool)
for t in range(len(time_target)):
    d = doy_target[t]
    hot_mask[t] = sst_target[t] >= thresholds[d]

# Per-cell MHW logic
# mhw_mask: (time, lat, lon)
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
n_time, n_lat, n_lon = sst_target.shape

for lat in range(n_lat):
    for lon in range(n_lon):
        if not sea_cells[lat, lon]:
            continue
        
        cell_hot = hot_mask[:, lat, lon]
        cell_mhw = np.zeros(n_time, dtype=bool)
        
        # Find runs of at least 5 hot days
        # Use a simple state machine or grouping
        runs = []
        start = None
        for t in range(n_time):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append((start, t-1))
                    start = None
        if start is not None:
            if n_time - start >= 5:
                runs.append((start, n_time-1))
        
        # Join runs separated by 1 or 2 non-hot days
        if not runs:
            continue
            
        merged_runs = []
        if runs:
            curr_start, curr_end = runs[0]
            for i in range(1, len(runs)):
                next_start, next_end = runs[i]
                if next_start - curr_end <= 3: # Gap of 1 or 2 days means next_start - curr_end is 2 or 3
                    # Wait, the instruction says "separated by 1 or 2 non-hot days".
                    # If curr_end is t1 and next_start is t2, the non-hot days are t1+1, ..., t2-1.
                    # Number of non-hot days = (t2-1) - (t1+1) + 1 = t2 - t1 - 1.
                    # t2 - t1 - 1 <= 2  =>  t2 - t1 <= 3.
                    curr_end = next_end
                else:
                    merged_runs.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged_runs.append((curr_start, curr_end))
            
        for s, e in merged_runs:
            cell_mhw[s:e+1] = True
        
        mhw_mask[:, lat, lon] = cell_mhw.astype(np.uint8)

# 4. Regional events
# a day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for t in range(n_time):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((time_target[start], time_target[t-1]))
            start = None
if start is not None:
    regional_events.append((time_target[start], time_target[n_time-1]))

# Results
import os
os.makedirs('output', exist_ok=True)

# Create NetCDF for mhw_mask
# Use xarray to save
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
    coords={
        "time": time_target,
        "latitude": ds_region.latitude.values,
        "longitude": ds_region.longitude.values,
    }
)
mhw_ds.to_netcdf("output/mhw_mask.nc")

# Report
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": BASELINE_START, "end": BASELINE_END},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": [
        {"onset": np.datetime64(onset).astype(datetime).strftime('%Y-%m-%d'),
         "end": np.datetime64(end).astype(datetime).strftime('%Y-%m-%d')}
        for onset, end in regional_events
    ],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Analysis complete. Files written.")
