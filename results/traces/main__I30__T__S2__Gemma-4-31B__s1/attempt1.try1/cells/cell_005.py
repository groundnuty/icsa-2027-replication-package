import xarray as xr
import fsspec
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

def get_doy(dt):
    year = dt.year
    doy = dt.timetuple().tm_yday
    # Non-leap years: Jan=31, Feb=28. Mar 1 is day 60 in tm_yday.
    # We want Mar 1 to be day 61.
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    if not is_leap and doy > 59:
        doy += 1
    return doy

fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89
target_start_str = '2010-06-01'
target_end_str = '2010-08-31'
baseline_start_date = pd.to_datetime('1992-01-01')
baseline_end_date = pd.to_datetime('2002-12-31')

os.makedirs('output', exist_ok=True)

with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    ds_region = ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max)
    )
    # Use a slightly wider range for baseline to accommodate +/- 5 day windows
    ds_baseline_full = ds_region.sel(time=slice('1991-12-20', '2003-01-10')).load()
    ds_target = ds_region.sel(time=slice(target_start_str, target_end_str)).load()

# Convert to float64
sst_baseline = ds_baseline_full.analysed_sst.values.astype(np.float64)
time_baseline = pd.to_datetime(ds_baseline_full.time.values)
sst_target = ds_target.analysed_sst.values.astype(np.float64)
time_target = pd.to_datetime(ds_target.time.values)

# Sea cells: SST finite on every day of the target period
mask_sea = np.all(np.isfinite(sst_target), axis=0)

# Precompute DOY for all baseline dates
baseline_doy = np.array([get_doy(t) for t in time_baseline])
baseline_period_mask = (time_baseline >= baseline_start_date) & (time_baseline <= baseline_end_date)

thresholds = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan, dtype=np.float64)
climatologies = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan, dtype=np.float64)

# Optimization: Group baseline dates by DOY
baseline_dates_by_doy = {}
for i, t in enumerate(time_baseline):
    d = get_doy(t)
    if d not in baseline_dates_by_doy:
        baseline_dates_by_doy[d] = []
    baseline_dates_by_doy[d].append(i)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Baseline dates b (1992-2002) with DOY d
    b_indices = [i for i in baseline_dates_by_doy.get(d, []) if baseline_period_mask[i]]
    if not b_indices:
        continue
    
    pool_indices = set()
    for b_idx in b_indices:
        for offset in range(-5, 6):
            idx = b_idx + offset
            if 0 <= idx < len(time_baseline):
                pool_indices.add(idx)
    
    pool_indices = sorted(list(pool_indices))
    pool_data = sst_baseline[pool_indices, :, :]
    
    # 90th percentile (hazen) and mean, ignoring NaN
    thresholds[d-1] = np.nanpercentile(pool_data, 90, axis=0, method='hazen')
    climatologies[d-1] = np.nanmean(pool_data, axis=0)

# Day 60: mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day centred moving mean (wraps around)
def smooth_array(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        window_indices = [(d + offset) % 366 for offset in range(-15, 16)]
        window_data = arr[window_indices]
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds_smooth = smooth_array(thresholds)
climatologies_smooth = smooth_array(climatologies)

# Per-cell MHWs
target_doy = np.array([get_doy(t) for t in time_target])
hot_days = np.zeros_like(sst_target, dtype=bool)

for t_idx in range(len(time_target)):
    d = target_doy[t_idx]
    hot_days[t_idx] = sst_target[t_idx] >= thresholds_smooth[d-1]

mhw_mask = np.zeros_like(hot_days, dtype=np.uint8)
for lat_idx in range(ds_region.latitude.size):
    for lon_idx in range(ds_region.longitude.size):
        if not mask_sea[lat_idx, lon_idx]:
            continue
            
        cell_hot = hot_days[:, lat_idx, lon_idx]
        
        # Find runs of hot days
        runs = []
        start = None
        for i in range(len(cell_hot)):
            if cell_hot[i]:
                if start is None:
                    start = i
            else:
                if start is not None:
                    runs.append((start, i - 1))
                    start = None
        if start is not None:
            runs.append((start, len(cell_hot) - 1))
            
        # Filter runs >= 5 days
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        if not mhw_runs:
            continue
            
        # Join gaps of 1 or 2 days
        merged_runs = []
        curr_start, curr_end = mhw_runs[0]
        for i in range(1, len(mhw_runs)):
            next_start, next_end = mhw_runs[i]
            if next_start - curr_end - 1 <= 2:
                curr_end = next_end
            else:
                merged_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged_runs.append((curr_start, curr_end))
            
        for start, end in merged_runs:
            mhw_mask[start:end+1, lat_idx, lon_idx] = 1

# Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for i in range(len(active_days)):
    if active_days[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            regional_events.append((time_target[start].strftime('%Y-%m-%d'), time_target[i-1].strftime('%Y-%m-%d')))
            start = None
if start is not None:
    regional_events.append((time_target[start].strftime('%Y-%m-%d'), time_target[-1].strftime('%Y-%m-%d')))

# Save Results
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": ds_target.time,
        "latitude": ds_region.latitude,
        "longitude": ds_region.longitude,
    }
)
ds_out.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": time_baseline[0].strftime('%Y-%m-%d'),
        "end": time_baseline[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": time_target[0].strftime('%Y-%m-%d'),
        "end": time_target[-1].strftime('%Y-%m-%d')
    },
    "events": [{"onset": e[0], "end": e[1]} for e in regional_events],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Successfully completed")
