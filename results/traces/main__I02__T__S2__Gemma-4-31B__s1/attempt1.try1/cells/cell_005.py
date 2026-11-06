import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import timedelta, date

# Create output directory
os.makedirs("output", exist_ok=True)

def get_day_of_year(dt):
    if isinstance(dt, np.datetime64):
        dt = pd.Timestamp(dt)
    m, d = dt.month, dt.day
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:m-1]) + d
    if m > 2:
        doy += 1
    return doy

# Setup
fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45
baseline_start_date = "1991-12-27"
baseline_end_date = "2003-01-05"
target_start_date = "2004-06-01"
target_end_date = "2004-08-31"

with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    subset = ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max)
    )
    baseline_ds = subset.sel(time=slice(baseline_start_date, baseline_end_date)).load()
    target_ds = subset.sel(time=slice(target_start_date, target_end_date)).load()

sst_baseline = baseline_ds.analysed_sst.values.astype(np.float64)
time_baseline = baseline_ds.time.values
sst_target = target_ds.analysed_sst.values.astype(np.float64)
time_target = target_ds.time.values

# 1. Sea cells: SST finite on every day of target period
sea_mask = np.all(np.isfinite(sst_target), axis=0)
n_time_target, n_lat, n_lon = sst_target.shape

# 2. Threshold and Climatology
baseline_dates_range = pd.date_range("1992-01-01", "2002-12-31")
baseline_times_all = pd.to_datetime(time_baseline)
time_to_idx = {t: i for i, t in enumerate(baseline_times_all)}

thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    d_dates = [date_val for date_val in baseline_dates_range if get_day_of_year(date_val) == d]
    pool_values = []
    for b_date in d_dates:
        for offset in range(-5, 6):
            t_win = b_date + timedelta(days=offset)
            if t_win in time_to_idx:
                pool_values.append(sst_baseline[time_to_idx[t_win]])
    
    if pool_values:
        pool_array = np.stack(pool_values)
        # method="hazen" for 90th percentile
        thresholds[d-1] = np.nanquantile(pool_array, 0.9, axis=0, method="hazen")
        climatology[d-1] = np.nanmean(pool_array, axis=0)

# Day 60 = mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

smoothed_thresholds = smooth(thresholds)
smoothed_climatology = smooth(climatology)

# 3. Per-cell MHWs
mhw_mask = np.zeros((n_time_target, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        
        cell_sst = sst_target[:, i, j]
        # Use get_day_of_year for each target date
        cell_thresholds = np.array([smoothed_thresholds[get_day_of_year(t)-1, i, j] for t in time_target])
        
        hot = cell_sst >= cell_thresholds
        is_mhw = np.zeros(n_time_target, dtype=bool)
        
        # Initial runs of >= 5
        runs = []
        start = None
        for t in range(n_time_target):
            if hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append((start, t-1))
                    start = None
        if start is not None:
            if n_time_target - start >= 5:
                runs.append((start, n_time_target-1))
        
        if not runs:
            continue
            
        # Join gaps of 1 or 2
        merged_runs = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            if next_start - curr_end - 1 <= 2:
                curr_end = next_end
            else:
                merged_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged_runs.append((curr_start, curr_end))
        
        for s, e in merged_runs:
            is_mhw[s:e+1] = True
            
        mhw_mask[:, i, j] = is_mhw.astype(np.uint8)

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for t in range(n_time_target):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((time_target[start], time_target[t-1]))
            start = None
if start is not None:
    regional_events.append((time_target[start], time_target[n_time_target-1]))

# Convert numpy.datetime64 to string "YYYY-MM-DD"
def format_date(np_dt):
    return pd.Timestamp(np_dt).strftime('%Y-%m-%d')

events_list = [{"onset": format_date(e[0]), "end": format_date(e[1])} for e in regional_events]

# Output NetCDF
ds_mhw = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": time_target,
        "latitude": subset.latitude.values,
        "longitude": subset.longitude.values,
    }
)
ds_mhw.to_netcdf("output/mhw_mask.nc")

# Output report
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": format_date(time_target[0]), "end": format_date(time_target[-1])},
    "events": events_list,
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done")
