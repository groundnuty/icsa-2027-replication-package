import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Ensure output directory exists
os.makedirs('output', exist_ok=True)

def get_fixed_doy(dt):
    month = dt.month
    day = dt.day
    if month == 1: return day
    if month == 2: return 31 + day
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[month-1] + day

# Load dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Target period
target_start = pd.Timestamp('2014-06-01')
target_end = pd.Timestamp('2014-08-31')
ds_target = ds_region.sel(time=slice(target_start, target_end)).load()
sst_target = ds_target.analysed_sst.values.astype(np.float64)

# Sea cells: SST is finite on every day of target period
sea_cells_mask = np.all(np.isfinite(sst_target), axis=0)

# Baseline period for data: 1991-12-27 to 2003-01-05
baseline_data_start = pd.Timestamp('1991-12-27')
baseline_data_end = pd.Timestamp('2003-01-05')
ds_baseline_full = ds_region.sel(time=slice(baseline_data_start, baseline_data_end)).load()
sst_baseline = ds_baseline_full.analysed_sst.values.astype(np.float64)
time_baseline = pd.to_datetime(ds_baseline_full.time.values)

# Arrays for thresholds and climatology (366, lat, lon)
thresholds = np.full((366, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype=np.float64)
climatologies = np.full((366, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype=np.float64)

# Thresholds and climatology computation
for d in range(1, 367):
    if d == 60:
        continue
    
    pool_mask = np.zeros(len(time_baseline), dtype=bool)
    found_baseline_date = False
    for i, t in enumerate(time_baseline):
        if pd.Timestamp('1992-01-01') <= t <= pd.Timestamp('2002-12-31'):
            if get_fixed_doy(t) == d:
                found_baseline_date = True
                start_idx = max(0, i - 5)
                end_idx = min(len(time_baseline) - 1, i + 5)
                pool_mask[start_idx : end_idx + 1] = True
                
    if found_baseline_date:
        pool_sst = sst_baseline[pool_mask]
        # method="hazen" for 90th percentile
        thresholds[d-1] = np.nanpercentile(pool_sst, 90, axis=0, method='hazen')
        climatologies[d-1] = np.nanmean(pool_sst, axis=0)

# Day 60 = mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing function
def smooth_366(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smoothed = smooth_366(thresholds)

# Target Period MHW Detection
target_times = pd.to_datetime(ds_target.time.values)
target_doys = np.array([get_fixed_doy(t) for t in target_times])
thresh_target = thresholds_smoothed[target_doys - 1]

# a day is hot if SST >= threshold
is_hot = sst_target >= thresh_target

mhw_mask = np.zeros_like(is_hot, dtype=np.uint8)

for lat_idx in range(sst_target.shape[1]):
    for lon_idx in range(sst_target.shape[2]):
        # Skip land cells immediately
        if not sea_cells_mask[lat_idx, lon_idx]:
            continue
            
        hot_days = is_hot[:, lat_idx, lon_idx]
        if not np.any(hot_days):
            continue
        
        runs = []
        start = None
        for i in range(len(hot_days)):
            if hot_days[i]:
                if start is None:
                    start = i
            else:
                if start is not None:
                    runs.append((start, i - 1))
                    start = None
        if start is not None:
            runs.append((start, len(hot_days) - 1))
            
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        if not mhw_runs:
            continue
            
        merged = []
        curr_start, curr_end = mhw_runs[0]
        for i in range(1, len(mhw_runs)):
            next_start, next_end = mhw_runs[i]
            if next_start - curr_end - 1 <= 2:
                curr_end = next_end
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
            
        for s, e in merged:
            mhw_mask[s:e+1, lat_idx, lon_idx] = 1

# Regional events
# Day is active if at least one sea cell is in a per-cell MHW
# (mhw_mask already 0 for land cells due to the sea_cells_mask check)
active_days = np.any(mhw_mask, axis=(1, 2))

regional_events = []
start = None
for i in range(len(active_days)):
    if active_days[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            regional_events.append((target_times[start].strftime('%Y-%m-%d'), 
                                   target_times[i-1].strftime('%Y-%m-%d')))
            start = None
if start is not None:
    regional_events.append((target_times[start].strftime('%Y-%m-%d'), 
                           target_times[-1].strftime('%Y-%m-%d')))

# Save results
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
    coords={
        "time": ds_target.time,
        "latitude": ds_region.latitude,
        "longitude": ds_region.longitude,
    },
)
ds_out.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": [{"onset": e[0], "end": e[1]} for e in regional_events],
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Analysis complete")
