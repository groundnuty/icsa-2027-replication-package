import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import os
import json

# --- Setup ---
fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

# --- Parameters ---
lat_min, lat_max = 63.31, 64.51
lon_min, lon_max = 21.31, 22.51
target_start = '2009-06-01'
target_end = '2009-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

# We need data for the baseline plus 5 days buffer
extended_baseline_start = '1991-12-27'
extended_baseline_end = '2003-01-05'

# --- Load Data ---
ds = xr.open_dataset(local_path, engine="h5netcdf")
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Target period slice
ds_target = ds_region.sel(time=slice(target_start, target_end)).astype('float64')
# Baseline period slice (extended)
ds_baseline = ds_region.sel(time=slice(extended_baseline_start, extended_baseline_end)).astype('float64')

# --- Utility Functions ---
def get_doy(date):
    """Map date to 1-366 as per instructions."""
    # month and day
    m = date.month
    d = date.day
    # Days in months for non-leap year
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = days_before[m-1] + d
    if m > 2 and date.is_leap:
        doy += 1
    # Adjust for 29 Feb
    # The instruction says: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
    # This is exactly the standard DOY for leap years. 
    # For non-leap years, Feb 28 is 59 and March 1 is 60.
    # But the instruction says "Non-leap years have no day 60".
    # This means in non-leap years, March 1 is still 61?
    # Let's re-read: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
    # This implies a fixed mapping based on (month, day).
    
    # Fixed mapping:
    # Jan: 1-31
    # Feb: 32-59
    # Feb 29: 60
    # Mar: 61-91 ...
    fixed_days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    # If it's Feb 29, it's 60. If it's March or later, we add 1 to the non-leap offset
    # to ensure March 1 is 61 regardless of leap year.
    if m == 2 and d == 29:
        return 60
    if m > 2:
        return fixed_days_before[m-1] + d + 1
    return fixed_days_before[m-1] + d

# --- Sea Cells ---
# Sea cells are grid cells whose SST is finite on every day of the target period.
sst_target = ds_target.analysed_sst.values # (time, lat, lon)
is_finite = np.all(np.isfinite(sst_target), axis=0)
sea_cells_mask = is_finite

# --- Thresholds and Climatology ---
# Prepare baseline data
sst_baseline = ds_baseline.analysed_sst.values # (time, lat, lon)
baseline_times = pd.to_datetime(ds_baseline.time.values)
baseline_doy = np.array([get_doy(t) for t in baseline_times])

# Actual baseline range: 1992-01-01 to 2002-12-31
baseline_mask = (baseline_times >= pd.Timestamp(baseline_start)) & (baseline_times <= pd.Timestamp(baseline_end))
baseline_dates = baseline_times[baseline_mask]

# Pools for d = 1 to 366 (excluding 60)
thresholds = np.full((367, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype='float64')
climatology = np.full((367, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype='float64')

# Pre-calculate dates for each d in baseline
baseline_dates_by_doy = {d: [] for d in range(1, 367)}
for t in baseline_dates:
    d = get_doy(t)
    if d != 60:
        baseline_dates_by_doy[d].append(t)

# To optimize, we can find all dates in the extended baseline that are within 5 days of any baseline date with DOY d.
extended_baseline_dates = pd.to_datetime(ds_baseline.time.values)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all dates t in extended_baseline_dates such that dist(t, baseline_date_with_doy_d) <= 5
    # For each baseline date with DOY d, we have a window.
    # The pool is the union of these windows.
    
    # Efficiently: find all dates in the extended set that fall into any of the windows.
    # All windows for a fixed d are separated by approx 1 year.
    # So we can just check each date in extended_baseline_dates.
    
    # But since the baseline is small (11 years), we can just iterate.
    pool_mask = np.zeros(len(extended_baseline_dates), dtype=bool)
    for t_base in baseline_dates_by_doy[d]:
        # Window is [t_base - 5, t_base + 5]
        start_win = t_base - pd.Timedelta(days=5)
        end_win = t_base + pd.Timedelta(days=5)
        # Mask dates in extended_baseline_dates that fall in this window
        pool_mask |= (extended_baseline_dates >= start_win) & (extended_baseline_dates <= end_win)
    
    # Extract SST for these dates
    pool_data = sst_baseline[pool_mask, :, :] # (num_days, lat, lon)
    
    # Threshold: 90th percentile (hazen)
    # numpy.nanpercentile with method='hazen'
    thresholds[d] = np.nanpercentile(pool_data, 90, axis=0, method='hazen')
    # Climatology: mean
    climatology[d] = np.nanmean(pool_data, axis=0)

# Handle day 60: mean of 59 and 61
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2

# Smoothing: 31-day moving mean (wrap around)
def smooth_wrap(arr):
    # arr shape: (367, lat, lon)
    # We only care about d=1..366.
    data = arr[1:] # (366, lat, lon)
    smoothed = np.zeros_like(data)
    for d in range(366):
        # Center d is index d (0-indexed).
        # Indices: (d-15) to (d+15) modulo 366.
        indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d] = np.nanmean(data[indices], axis=0)
    return smoothed

smoothed_thresholds = smooth_wrap(thresholds)
smoothed_climatology = smooth_wrap(climatology)

# --- Per-Cell MHWs ---
# target period: 2009-06-01 to 2009-08-31
target_times = pd.to_datetime(ds_target.time.values)
target_doys = np.array([get_doy(t) for t in target_times])

# SST target
sst_vals = sst_target # (time, lat, lon)
# Thresholds for these days
# smoothed_thresholds is (366, lat, lon).
# target_doys are 1..366.
target_thresh = smoothed_thresholds[target_doys - 1] # (time, lat, lon)

# Hot days: SST >= threshold
is_hot = (sst_vals >= target_thresh) # (time, lat, lon)

# We only care about sea cells.
# Land cells are not hot.
is_hot = is_hot & sea_cells_mask[np.newaxis, :, :]

# Detect MHWs per cell
# a per-cell MHW is a run of >= 5 consecutive hot days.
# Gaps of 1 or 2 non-hot days are joined.

mhw_mask = np.zeros_like(is_hot, dtype='uint8')

# Process each cell
for lat_idx in range(sst_vals.shape[1]):
    for lon_idx in range(sst_vals.shape[2]):
        if not sea_cells_mask[lat_idx, lon_idx]:
            continue
        
        cell_hot = is_hot[:, lat_idx, lon_idx]
        # Find runs of hot days
        # This is a 1D array of booleans.
        # Use a simple loop or grouping to find MHWs.
        
        # Standard MHW detection:
        # 1. Find runs of >= 5 hot days.
        # 2. Join runs if gap <= 2 days.
        
        # First, find all hot runs
        runs = []
        start = None
        for i in range(len(cell_hot)):
            if cell_hot[i] and start is None:
                start = i
            elif not cell_hot[i] and start is not None:
                if i - start >= 5:
                    runs.append([start, i-1])
                start = None
        if start is not None and len(cell_hot) - start >= 5:
            runs.append([start, len(cell_hot)-1])
        
        if not runs:
            continue
            
        # Now join runs with gap <= 2
        joined_runs = []
        if runs:
            curr_start, curr_end = runs[0]
            for i in range(1, len(runs)):
                next_start, next_end = runs[i]
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    joined_runs.append([curr_start, curr_end])
                    curr_start, curr_end = next_start, next_end
            joined_runs.append([curr_start, curr_end])
            
        for start, end in joined_runs:
            mhw_mask[start:end+1, lat_idx, lon_idx] = 1

# --- Regional Events ---
# a day is active if at least one sea cell is in a per-cell MHW.
active_days = np.any(mhw_mask == 1, axis=(1, 2))
# regional MHW event: maximal run of consecutive active days.
regional_events = []
start = None
for i in range(len(active_days)):
    if active_days[i] and start is None:
        start = i
    elif not active_days[i] and start is not None:
        regional_events.append({
            "onset": target_times[start].strftime('%Y-%m-%d'),
            "end": target_times[i-1].strftime('%Y-%m-%d')
        })
        start = None
if start is not None:
    regional_events.append({
        "onset": target_times[start].strftime('%Y-%m-%d'),
        "end": target_times[-1].strftime('%Y-%m-%d')
    })

# --- Output ---
# 1. mhw_mask.nc
# Dimensions: (time, latitude, longitude)
# Variables: mhw (uint8)
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": ds_target.time,
        "latitude": ds_region.latitude,
        "longitude": ds_region.longitude
    }
)
os.makedirs('output', exist_ok=True)
mhw_ds.to_netcdf('output/mhw_mask.nc')

# 2. report.json
report = {
    "region": {
        "lat_min": float(lat_min),
        "lat_max": float(lat_max),
        "lon_min": float(lon_min),
        "lon_max": float(lon_max),
    },
    "baseline_analysed": {
        "start": extended_baseline_start,
        "end": extended_baseline_end,
    },
    "target_analysed": {
        "start": target_start,
        "end": target_end,
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Successfully completed.")
