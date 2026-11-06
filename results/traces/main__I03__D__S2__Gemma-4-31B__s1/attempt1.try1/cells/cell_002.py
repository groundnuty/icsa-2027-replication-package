import xarray as xr
import numpy as np
import pandas as pd
import json
import fsspec
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
fs = fsspec.filesystem('onedata')
fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine="h5netcdf")
sst_var = 'analysed_sst'

# Slice region
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Target period SST
ds_target = ds_reg.sel(time=slice(target_start_str, target_end_str))
target_times = ds_target.time.values

# Sea cells: SST finite on every day of the target period
# Finite means not NaN and not inf
sst_target = ds_target[sst_var].values.astype(np.float64)
# Mask for cells that have any NaN or Inf during the target period
# sst_target shape: (time, lat, lon)
is_finite = np.all(np.isfinite(sst_target), axis=0)

# Expanded baseline SST
ds_baseline_exp = ds_reg.sel(time=slice(expanded_start_str, expanded_end_str))
sst_baseline = ds_baseline_exp[sst_var].values.astype(np.float64)
baseline_times = pd.to_datetime(ds_baseline_exp.time.values)

def get_day_of_year(dt):
    # 1 Jan = 1, ..., 29 Feb = 60, ..., 31 Dec = 366
    # pandas .dayofyear is 1-366
    return dt.dayofyear

# Precompute day of year for baseline
baseline_doy = np.array([get_day_of_year(t) for t in baseline_times])

# Thresholds and Climatology
# Shape: (lat, lon, 366)
n_lat = sst_target.shape[1]
n_lon = sst_target.shape[2]
thresholds = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
climatology = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)

# For each day of year d other than 60
for d in range(1, 367):
    if d == 60:
        continue
    
    # Pool: every SST value whose date lies within +/- 5 calendar days of a baseline date (1992-2002) whose doy is d.
    # Baseline dates in [1992-01-01, 2002-12-31]
    baseline_mask = (baseline_times >= pd.Timestamp(baseline_start_str)) & (baseline_times <= pd.Timestamp(baseline_end_str))
    baseline_doy_mask = (baseline_doy == d) & baseline_mask
    
    # Dates in baseline that have doy == d
    target_baseline_dates = baseline_times[baseline_doy_mask]
    
    if len(target_baseline_dates) == 0:
        continue

    # For each such date, we need a window +/- 5 days.
    # The pool is the union of all these windows.
    # Since we can have multiple years, we find all dates that are within 5 days of ANY target_baseline_date.
    
    # To optimize: find the total set of dates in the expanded baseline
    # that are within 5 days of any date in target_baseline_dates.
    # A date 't' is in the pool if there exists a 'b' in target_baseline_dates such that |t-b| <= 5 days.
    
    # For a fixed d, the dates in the expanded baseline that satisfy this are:
    # For each year y in 1992..2002:
    #   date b_y = date with doy d in year y
    #   window [b_y - 5, b_y + 5]
    
    # Let's find the indices in the expanded baseline dataset.
    pool_indices = []
    for b_date in target_baseline_dates:
        # Window [b_date - 5, b_date + 5]
        win_start = b_date - pd.Timedelta(days=5)
        win_end = b_date + pd.Timedelta(days=5)
        
        # Find indices in baseline_times that fall in this window
        idx_start = np.searchsorted(baseline_times, win_start)
        idx_end = np.searchsorted(baseline_times, win_end, side='right')
        pool_indices.extend(range(idx_start, idx_end))
    
    unique_indices = np.unique(pool_indices)
    
    # Extract SST for these indices: (len(unique_indices), lat, lon)
    pool_sst = sst_baseline[unique_indices, :, :]
    
    # Threshold: 90th percentile (method='hazen')
    # Climatology: mean
    # np.nanpercentile does not have 'hazen' as a standard option.
    # MATLAB's quantile(X, 0.9) is Hyndman-Fan type 5.
    # Numpy's method='hazen' is equivalent to that.
    thresholds[:, :, d-1] = np.nanpercentile(pool_sst, 90, axis=0, method='hazen')
    climatology[:, :, d-1] = np.nanmean(pool_sst, axis=0)

# Day 60: mean of 59 and 61
thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
climatology[:, :, 59] = (climatology[:, :, 58] + climatology[:, :, 60]) / 2

# Smoothing: 31-day moving mean, wrapping
def smooth_366(arr):
    # arr shape: (lat, lon, 366)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # Days d-15 to d+15 modulo 366
        # Indices: (d - 15 + i) % 366 for i in 0..30
        indices = np.arange(d - 15, d + 16) % 366
        window_data = arr[:, :, indices]
        smoothed[:, :, d] = np.nanmean(window_data, axis=2)
    return smoothed

thresholds_smoothed = smooth_366(thresholds)
climatology_smoothed = smooth_366(climatology)

# Target period analysis
# target_times: numpy datetime64
target_doy = np.array([pd.to_datetime(t).dayofyear for t in target_times])

# SST: (time, lat, lon)
# Thresholds: (lat, lon, 366)
# We need threshold for each day: (time, lat, lon)
# d-1 for 0-indexing
thresh_target = thresholds_smoothed[np.newaxis, :, :][:, :, :, target_doy - 1]
# Wait, thresholds_smoothed is (lat, lon, 366). 
# Target doy is (time,).
# Need to transpose or index correctly.
# thresholds_smoothed[:, :, target_doy - 1] would be (lat, lon, time)
thresh_target = np.transpose(thresholds_smoothed[:, :, target_doy - 1], (2, 0, 1))

# Hot days: SST >= threshold
is_hot = (sst_target >= thresh_target)

# Per-cell MHWs
# is_hot: (time, lat, lon)
mhw_mask = np.zeros_like(is_hot, dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not is_finite[i, j]:
            continue
        
        cell_hot = is_hot[:, i, j]
        # Find runs of at least 5 hot days
        # and join gaps of 1-2 days
        
        # Simple run detection
        n_days = len(cell_hot)
        in_mhw = np.zeros(n_days, dtype=bool)
        
        # Identify all hot runs
        # A simple way to find runs:
        # Use a grouping approach or just iterate
        
        # First, identify all runs of >= 5 hot days
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
            
        # Join runs separated by 1 or 2 non-hot days
        # This needs to be done iteratively until no more joins
        merged = True
        while merged:
            merged = False
            new_runs = []
            if not hot_runs:
                break
            
            # Sort runs by start
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
# Day is active if at least one sea cell is in a per-cell MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))
# active_days: (time,)

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
# mhw_mask.nc
# Dimensions: time, lat, lon
# Coordinates: time, latitude, longitude
ds_mhw = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_times,
        "latitude": ds_reg.latitude.values,
        "longitude": ds_reg.longitude.values,
    },
)
ds_mhw.to_netcdf("output/mhw_mask.nc")

# report.json
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
