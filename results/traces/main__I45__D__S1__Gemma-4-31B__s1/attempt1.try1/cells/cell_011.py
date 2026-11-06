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
    """Map date to 1-366 as per instructions.
    1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366.
    """
    # Handle pandas Timestamp or datetime object
    m = date.month
    d = date.day
    # Fixed mapping to ensure consistency across leap years
    # Days before the start of the month (for non-leap year)
    fixed_days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    
    if m == 2 and d == 29:
        return 60
    if m > 2:
        return fixed_days_before[m-1] + d + 1
    return fixed_days_before[m-1] + d

# --- Sea Cells ---
sst_target = ds_target.analysed_sst.values # (time, lat, lon)
is_finite = np.all(np.isfinite(sst_target), axis=0)
sea_cells_mask = is_finite

# --- Thresholds and Climatology ---
sst_baseline = ds_baseline.analysed_sst.values # (time, lat, lon)
baseline_times = pd.to_datetime(ds_baseline.time.values)
# Note: baseline_times is an array of Timestamps

# Baseline range: 1992-01-01 to 2002-12-31
baseline_mask = (baseline_times >= pd.Timestamp(baseline_start)) & (baseline_times <= pd.Timestamp(baseline_end))
baseline_dates = baseline_times[baseline_mask]

# Pools for d = 1 to 366 (excluding 60)
thresholds = np.full((367, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype='float64')
climatology = np.full((367, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype='float64')

baseline_dates_by_doy = {d: [] for d in range(1, 367)}
for t in baseline_dates:
    d = get_doy(t)
    if d != 60:
        baseline_dates_by_doy[d].append(t)

extended_baseline_dates = pd.to_datetime(ds_baseline.time.values)

for d in range(1, 367):
    if d == 60:
        continue
    
    pool_mask = np.zeros(len(extended_baseline_dates), dtype=bool)
    for t_base in baseline_dates_by_doy[d]:
        start_win = t_base - pd.Timedelta(days=5)
        end_win = t_base + pd.Timedelta(days=5)
        pool_mask |= (extended_baseline_dates >= start_win) & (extended_baseline_dates <= end_win)
    
    pool_data = sst_baseline[pool_mask, :, :] # (num_days, lat, lon)
    
    # Threshold: 90th percentile (hazen)
    thresholds[d] = np.nanpercentile(pool_data, 90, axis=0, method='hazen')
    # Climatology: mean
    climatology[d] = np.nanmean(pool_data, axis=0)

# Handle day 60: mean of 59 and 61
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2

# Smoothing: 31-day moving mean (wrap around)
def smooth_wrap(arr):
    # arr shape: (367, lat, lon)
    data = arr[1:] # (366, lat, lon)
    smoothed = np.zeros_like(data)
    for d in range(366):
        # Indices: (d-15) to (d+15) modulo 366
        indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d] = np.nanmean(data[indices], axis=0)
    return smoothed

smoothed_thresholds = smooth_wrap(thresholds)
smoothed_climatology = smooth_wrap(climatology)

# --- Per-Cell MHWs ---
target_times = pd.to_datetime(ds_target.time.values)
target_doys = np.array([get_doy(t) for t in target_times])

sst_vals = sst_target # (time, lat, lon)
target_thresh = smoothed_thresholds[target_doys - 1] # (time, lat, lon)

is_hot = (sst_vals >= target_thresh) # (time, lat, lon)
is_hot = is_hot & sea_cells_mask[np.newaxis, :, :]

mhw_mask = np.zeros_like(is_hot, dtype='uint8')

# Detect MHWs per cell
for lat_idx in range(sst_vals.shape[1]):
    for lon_idx in range(sst_vals.shape[2]):
        if not sea_cells_mask[lat_idx, lon_idx]:
            continue
        
        cell_hot = is_hot[:, lat_idx, lon_idx]
        
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
            
        joined_runs = []
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
active_days = np.any(mhw_mask == 1, axis=(1, 2))
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
