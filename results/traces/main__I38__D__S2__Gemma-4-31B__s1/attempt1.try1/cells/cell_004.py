import xarray as xr
import numpy as np
import pandas as pd
import json
import fsspec
from datetime import datetime, timedelta

# Initialize filesystem
fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
if not fsspec.filesystem('onedata').exists(remote_path):
    # This is just a safety check, it should exist.
    pass
fs.get(remote_path, local_path)

# Open dataset
ds = xr.open_dataset(local_path, engine="h5netcdf")

# Region and Period
lat_min, lat_max = 60.49, 61.69
lon_min, lon_max = 17.25, 18.45
target_start_dt = pd.to_datetime('2003-06-01')
target_end_dt = pd.to_datetime('2003-08-31')
baseline_start_dt = pd.to_datetime('1992-01-01')
baseline_end_dt = pd.to_datetime('2002-12-31')

# Window bounds for pooling
# Baseline window expands by 5 days on either side
window_start_dt = pd.to_datetime('1991-12-27')
window_end_dt = pd.to_datetime('2003-01-05')

# Slice the region and time to minimize memory
# We need the window for baseline and the target period.
# The window ends 2003-01-05, but target period is June-Aug 2003.
# So we take everything from 1991-12-27 to 2003-08-31.
ds_region = ds.sel(
    latitude=slice(lat_min, lat_max),
    longitude=slice(lon_min, lon_max),
    time=slice(window_start_dt, target_end_dt)
).astype(np.float64)

sst = ds_region['analysed_sst']

# 1. Sea cells: finite on every day of the target period
target_sst = sst.sel(time=slice(target_start_dt, target_end_dt))
sea_cells_mask = np.isfinite(target_sst).all(dim='time')

# 2. Threshold and Climatology
def get_doy(dt):
    # 1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    # Non-leap years have no day 60.
    doy = dt.timetuple().tm_yday
    if not dt.is_leap_year and doy >= 60:
        return doy + 1
    return doy

# Map all times in the window to DOY
times = pd.to_datetime(sst.time.values)
time_to_idx = {t: i for i, t in enumerate(times)}

# Baseline dates (1992-01-01 to 2002-12-31)
baseline_dates = pd.date_range(baseline_start_dt, baseline_end_dt)

# Initialize threshold and climatology arrays
thresholds = np.full((367, len(sst.latitude), len(sst.longitude)), np.nan, dtype=np.float64)
climatologies = np.full((367, len(sst.latitude), len(sst.longitude)), np.nan, dtype=np.float64)

# For each DOY d from 1 to 366, d != 60
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find baseline dates with DOY d
    b_dates = [dt for dt in baseline_dates if get_doy(dt) == d]
    
    # Find all dates in the window [b-5, b+5] for all b in b_dates
    pool_dates = set()
    for b in b_dates:
        for offset in range(-5, 6):
            pool_dates.add(b + timedelta(days=offset))
    
    # Convert pool_dates to indices of sst.time
    indices = [time_to_idx[t] for t in pool_dates if t in time_to_idx]
    
    if not indices:
        continue
        
    # Pool of SST values
    pool = sst.values[indices, :, :]
    
    # Compute 90th percentile (Hazen) and mean
    thresholds[d] = np.nanpercentile(pool, 90, axis=0, method='hazen')
    climatologies[d] = np.nanmean(pool, axis=0)

# Handle DOY 60
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatologies[60] = (climatologies[59] + climatologies[61]) / 2

# Smooth with 31-day moving mean (wraps around)
def smooth_366(arr):
    data = arr[1:] # (366, lat, lon)
    smoothed = np.zeros_like(data)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d] = np.nanmean(data[indices], axis=0)
    return smoothed

smoothed_thresholds = smooth_366(thresholds)
# smoothed_climatologies = smooth_366(climatologies) # Not needed for MHW detection but computed for completeness

# 3. Per-cell MHWs
target_sst_vals = target_sst.values
target_times = pd.to_datetime(target_sst.time.values)
target_doys = np.array([get_doy(t) for t in target_times])

# Thresholds for target days (target_doys are 1..366 -> index 0..365)
target_thresh_vals = smoothed_thresholds[target_doys - 1]

# A day is hot if SST >= threshold
hot_days = target_sst_vals >= target_thresh_vals

# Run detection per cell
mhw_mask = np.zeros_like(hot_days, dtype=np.uint8)

for lat_idx in range(hot_days.shape[1]):
    for lon_idx in range(hot_days.shape[2]):
        # Check if it's a sea cell
        if not sea_cells_mask.values[lat_idx, lon_idx]:
            continue
            
        cell_hot = hot_days[:, lat_idx, lon_idx]
        if not np.any(cell_hot):
            continue
        
        n_days = len(cell_hot)
        is_mhw = np.zeros(n_days, dtype=bool)
        
        # Find all runs of hot days
        runs = []
        start = None
        for i in range(n_days):
            if cell_hot[i] and start is None:
                start = i
            elif not cell_hot[i] and start is not None:
                runs.append((start, i - 1))
                start = None
        if start is not None:
            runs.append((start, n_days - 1))
            
        # Filter runs >= 5 days
        valid_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Join runs separated by 1 or 2 days
        if not valid_runs:
            continue
            
        joined_runs = []
        curr_start, curr_end = valid_runs[0]
        for next_start, next_end in valid_runs[1:]:
            if next_start - curr_end <= 3:
                curr_end = next_end
            else:
                joined_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        joined_runs.append((curr_start, curr_end))
            
        for start, end in joined_runs:
            is_mhw[start : end + 1] = True
        
        mhw_mask[:, lat_idx, lon_idx] = is_mhw.astype(np.uint8)

# 4. Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for i in range(len(active_days)):
    if active_days[i] and start is None:
        start = i
    elif not active_days[i] and start is not None:
        regional_events.append((target_times[start], target_times[i-1]))
        start = None
if start is not None:
    regional_events.append((target_times[start], target_times[-1]))

# Final Output
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_sst.time,
        "latitude": sst.latitude,
        "longitude": sst.longitude,
    }
)
mhw_ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start_dt.strftime('%Y-%m-%d'), "end": baseline_end_dt.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start_dt.strftime('%Y-%m-%d'), "end": target_end_dt.strftime('%Y-%m-%d')},
    "events": [{"onset": e[0].strftime('%Y-%m-%d'), "end": e[1].strftime('%Y-%m-%d')} for e in regional_events],
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Analysis complete.")
