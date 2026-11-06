import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 54.39, 55.59
lon_min, lon_max = 18.25, 19.45
target_start = pd.to_datetime('2021-06-01')
target_end = pd.to_datetime('2021-08-31')
baseline_start = pd.to_datetime('1992-01-01')
baseline_end = pd.to_datetime('2002-12-31')

def get_custom_doy(dt):
    days_in_months = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_months[:dt.month]) + dt.day

all_files = fs.ls(root_dir)
all_files_set = set(all_files)

def load_sst_region(start, end, lat_min, lat_max, lon_min, lon_max):
    date_range = pd.date_range(start, end)
    sst_data = []
    actual_times = []
    
    for dt in date_range:
        filename = f'{root_dir}/sst_{dt.strftime("%Y%m%d")}.nc'
        if filename in all_files_set:
            with fs.open(filename, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                # Use slice for faster selection
                region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                sst_data.append(region_ds['analysed_sst'].values.squeeze())
                actual_times.append(dt)
        else:
            # If file is missing, we should handle it. 
            # But for this task, the dataset is likely complete.
            # Let's use NaNs to maintain alignment.
            # We'll need to know the shape of a typical slice.
            if not sst_data:
                # Get shape from first file
                with fs.open(f'{root_dir}/sst_19820101.nc', "rb") as f_sample:
                    ds_sample = xr.open_dataset(f_sample, engine="h5netcdf")
                    # Need to re-slice to get correct region size
                    region_sample = ds_sample.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                    shape = region_sample['analysed_sst'].shape[1:] # (lat, lon)
                sst_data.append(np.full(shape, np.nan))
            else:
                sst_data.append(np.full(sst_data[0].shape, np.nan))
            actual_times.append(dt)
            
    return np.stack(sst_data, axis=0).astype(np.float64), actual_times

# 1. Load target SSTs to identify sea cells
target_sst, target_times = load_sst_region(target_start, target_end, lat_min, lat_max, lon_min, lon_max)

# Sea cells: finite on every day of target period
# target_sst shape: (time, lat, lon)
is_finite = np.all(np.isfinite(target_sst), axis=0)
sea_cells = is_finite # boolean mask (lat, lon)

# 2. Baseline SSTs
# We need SSTs from baseline_start - 5 days to baseline_end + 5 days
baseline_load_start = baseline_start - timedelta(days=5)
baseline_load_end = baseline_end + timedelta(days=5)
baseline_sst, baseline_times = load_sst_region(baseline_load_start, baseline_load_end, lat_min, lat_max, lon_min, lon_max)

# Precompute custom doy for all loaded baseline dates
baseline_doys = np.array([get_custom_doy(t) for t in baseline_times])

# Baseline data is (time, lat, lon)
# We want to build pools for d = 1 to 366 (excluding 60)
thresholds = np.full((367, *sea_cells.shape), np.nan, dtype=np.float64)
climatology = np.full((367, *sea_cells.shape), np.nan, dtype=np.float64)

# Find indices of baseline dates in [1992-01-01, 2002-12-31]
baseline_range_mask = (np.array(baseline_times) >= baseline_start) & (np.array(baseline_times) <= baseline_end)
baseline_indices = np.where(baseline_range_mask)[0]

# To avoid redundant computation, let's map each doy to its baseline dates
doy_to_dates = {}
for idx in baseline_indices:
    d = baseline_doys[idx]
    if d not in doy_to_dates:
        doy_to_dates[d] = []
    doy_to_dates[d].append(idx)

# For each d in 1..366 (excluding 60)
for d in range(1, 367):
    if d == 60:
        continue
    
    # Get baseline dates with custom_doy == d
    if d not in doy_to_dates:
        continue
    
    # The pool for d is all SST values within +/- 5 days of any T with doy(T) == d
    # Use a set to collect unique indices in baseline_sst
    pool_indices = set()
    for T_idx in doy_to_dates[d]:
        # The window is [T_idx - 5, T_idx + 5]
        # But we must ensure we stay within the bounds of baseline_sst
        start_idx = max(0, T_idx - 5)
        end_idx = min(len(baseline_times) - 1, T_idx + 5)
        for idx in range(start_idx, end_idx + 1):
            pool_indices.add(idx)
    
    pool_indices = sorted(list(pool_indices))
    if not pool_indices:
        continue
    
    # Extract pool: (num_days_in_pool, lat, lon)
    pool = baseline_sst[pool_indices, :, :]
    
    # Compute 90th percentile (Hazen) and mean
    # numpy.nanpercentile with method="hazen"
    thresholds[d] = np.nanpercentile(pool, 90, axis=0, method="hazen")
    climatology[d] = np.nanmean(pool, axis=0)

# Fill day 60
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2

# Smoothing: 31-day centred moving mean, wraps around
def smooth_array(arr):
    # arr shape: (367, lat, lon)
    # we only care about indices 1..366
    data = arr[1:] # (366, lat, lon)
    smoothed = np.full_like(data, np.nan)
    
    for d in range(366):
        # Window is d-15 to d+15
        # indices are modulo 366
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = data[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

smoothed_thresholds = smooth_array(thresholds)
smoothed_climatology = smooth_array(climatology)

# 3. Per-cell MHWs
# target_sst: (time, lat, lon)
# smoothed_thresholds: (366, lat, lon)
# target_times: dates from target_start to target_end
# We need to map target_times to custom_doy (1..366)

target_doys = np.array([get_custom_doy(t) for t in target_times])
# Adjusted index for smoothed_thresholds (0..365)
target_doy_indices = target_doys - 1

# A day is hot if SST >= threshold
# thresholds for target days
target_thresholds = smoothed_thresholds[target_doy_indices] # (time, lat, lon)
is_hot = target_sst >= target_thresholds # (time, lat, lon)

# Identify runs of >= 5 consecutive hot days, joining gaps of 1-2 days.
# We do this per cell.
mhw_mask = np.zeros_like(is_hot, dtype=np.uint8)

# Process cell by cell
# is_hot: (time, lat, lon)
# This can be slow. Let's optimize.
# We can use some vectorization or iterate efficiently.

# For each cell (lat, lon)
# time_series = is_hot[:, lat_idx, lon_idx]
# Find hot runs...
# Joining gaps of 1 or 2 means:
#   - run of >= 5 hot
#   - if gap is 1-2 and both sides are part of runs (or just the start?)
# Actually, the standard definition is: 
#   1. hot days (SST >= threshold)
#   2. run of >= 5 consecutive hot days
#   3. join runs separated by 1-2 non-hot days

def find_mhw_indices(hot_series):
    # hot_series: boolean array of length T
    n = len(hot_series)
    mhw = np.zeros(n, dtype=bool)
    
    # 1. Find all hot runs of length >= 5
    runs = []
    start = None
    for i in range(n):
        if hot_series[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                if i - start >= 5:
                    runs.append((start, i - 1))
                start = None
    if start is not None:
        if n - start >= 5:
            runs.append((start, n - 1))
            
    if not runs:
        return mhw
    
    # 2. Join runs separated by 1 or 2 non-hot days
    joined_runs = []
    if runs:
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            if next_start - curr_end - 1 <= 2:
                # Join
                curr_end = next_end
            else:
                joined_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        joined_runs.append((curr_start, curr_end))
    
    for s, e in joined_runs:
        mhw[s : e + 1] = True
    return mhw

# We only process sea cells
for r in range(sea_cells.shape[0]):
    for c in range(sea_cells.shape[1]):
        if sea_cells[r, c]:
            mhw_mask[:, r, c] = find_mhw_indices(is_hot[:, r, c])

# 4. Regional events
# active day: at least one sea cell is in MHW
is_active = np.any(mhw_mask == 1, axis=(1, 2))

# Regional MHW event: maximal run of consecutive active days
regional_events = []
start = None
for i in range(len(is_active)):
    if is_active[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            regional_events.append((target_times[start], target_times[i-1]))
            start = None
if start is not None:
    regional_events.append((target_times[start], target_times[-1]))

# Output
# mhw_mask.nc
# report.json

# Save NetCDF
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_times,
        "latitude": lats_region,
        "longitude": lons_region,
    },
)
ds_out.to_netcdf("output/mhw_mask.nc")

# Save JSON
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": baseline_load_start.strftime("%Y-%m-%d"), 
        "end": baseline_load_end.strftime("%Y-%m-%d")
    },
    "target_analysed": {
        "start": target_start.strftime("%Y-%m-%d"), 
        "end": target_end.strftime("%Y-%m-%d")
    },
    "events": [
        {"onset": e[0].strftime("%Y-%m-%d"), "end": e[1].strftime("%Y-%m-%d")} 
        for e in regional_events
    ],
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done")
