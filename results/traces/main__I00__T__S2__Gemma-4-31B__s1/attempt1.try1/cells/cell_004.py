import xarray as xr
import fsspec
import numpy as np
import pandas as pd
import json
from datetime import timedelta
import os

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

def get_doy(date):
    # 1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[date.month - 1] + date.day

# Params
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
target_start = pd.Timestamp('2004-06-01')
target_end = pd.Timestamp('2004-08-31')

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Slice region and time
    # Baseline dates: 1992-01-01 to 2002-12-31. 
    # Window +/- 5 days: 1991-12-27 to 2003-01-05.
    # Target: 2004-06-01 to 2004-08-31.
    ds_subset = ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max),
        time=slice('1991-12-27', '2004-08-31')
    ).load()

sst = ds_subset['analysed_sst'].astype(np.float64)

# 1. Sea cells: finite SST on every day of target period
target_sst = sst.sel(time=slice(target_start, target_end))
is_finite = np.isfinite(target_sst)
sea_mask = is_finite.all(dim='time')

# 2. Threshold and climatology
baseline_dates = pd.date_range(baseline_start, baseline_end)
all_dates = pd.to_datetime(ds_subset.time.values)
date_to_idx = {d: i for i, d in enumerate(all_dates)}

doy_pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    
    S_d = [date for date in baseline_dates if get_doy(date) == d]
    pool_dates = set()
    for D in S_d:
        for delta in range(-5, 6):
            pool_dates.add(D + timedelta(days=delta))
    
    pool_indices = [date_to_idx[d] for d in pool_dates if d in date_to_idx]
    doy_pools[d] = pool_indices

thresholds = np.full((366, sst.latitude.size, sst.longitude.size), np.nan)
climatologies = np.full((366, sst.latitude.size, sst.longitude.size), np.nan)

sst_values = sst.values

for d in range(1, 367):
    if d == 60:
        continue
    
    indices = doy_pools[d]
    pool_data = sst_values[indices, :, :]
    
    # method="hazen" is the one that matches MATLAB's quantile default (Hyndman-Fan type 5)
    thresholds[d-1] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
    climatologies[d-1] = np.nanmean(pool_data, axis=0)

# Handle day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

def smooth(arr):
    smoothed = np.zeros_like(arr)
    for i in range(366):
        indices = [(i + k) % 366 for k in range(-15, 16)]
        smoothed[i] = np.nanmean(arr[indices], axis=0)
    return smoothed

thresholds = smooth(thresholds)
climatologies = smooth(climatologies)

# 3. Per-cell MHWs
target_sst_vals = target_sst.values
target_times = pd.to_datetime(target_sst.time.values)

target_thresholds = []
for t in target_times:
    d = get_doy(t)
    target_thresholds.append(thresholds[d-1])
target_thresholds = np.array(target_thresholds)

is_hot = (target_sst_vals >= target_thresholds)
is_hot = is_hot & sea_mask.values

mhw_mask = np.zeros_like(is_hot, dtype=np.uint8)
n_time, n_lat, n_lon = is_hot.shape

for lat in range(n_lat):
    for lon in range(n_lon):
        cell_hot = is_hot[:, lat, lon]
        if not np.any(cell_hot):
            continue
            
        runs = []
        start = None
        for i in range(n_time):
            if cell_hot[i]:
                if start is None:
                    start = i
            else:
                if start is not None:
                    runs.append((start, i - 1))
                    start = None
        if start is not None:
            runs.append((start, n_time - 1))
            
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        if not mhw_runs:
            continue
            
        joined_runs = []
        curr_start, curr_end = mhw_runs[0]
        for i in range(1, len(mhw_runs)):
            next_start, next_end = mhw_runs[i]
            if next_start - curr_end - 1 <= 2:
                curr_end = next_end
            else:
                joined_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        joined_runs.append((curr_start, curr_end))
            
        for start, end in joined_runs:
            mhw_mask[start:end+1, lat, lon] = 1

# 4. Regional events
is_active = np.any(mhw_mask == 1, axis=(1, 2))
events = []
start = None
for i in range(n_time):
    if is_active[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            events.append((target_times[start], target_times[i-1]))
            start = None
if start is not None:
    events.append((target_times[start], target_times[n_time-1]))

# Outputs
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_sst.time,
        "latitude": target_sst.latitude,
        "longitude": target_sst.longitude
    }
)
mhw_ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start.strftime('%Y-%m-%d'), "end": baseline_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": [{"onset": e[0].strftime('%Y-%m-%d'), "end": e[1].strftime('%Y-%m-%d')} for e in events],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Success")
