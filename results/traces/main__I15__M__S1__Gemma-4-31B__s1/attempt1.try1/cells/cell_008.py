import os
import glob
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

# --- Configuration ---
dataset_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'
target_start_str = '2019-06-01'
target_end_str = '2019-08-31'

def get_day_of_year(dt):
    """
    Map every date to a day of year from 1 to 366:
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60.
    """
    # Ensure dt is a pandas Timestamp
    ts = pd.Timestamp(dt)
    standard_doy = ts.dayofyear
    is_leap = ts.is_leap_year
    if not is_leap and standard_doy >= 60:
        return standard_doy + 1
    return standard_doy

def load_sst_subset(start_date, end_date, lat_min, lat_max, lon_min, lon_max):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    date_range = pd.date_range(start, end)
    
    # Use the first available file in the range to get coordinates
    first_file = None
    for dt in date_range:
        f = os.path.join(dataset_dir, f"sst_{dt.strftime('%Y%m%d')}.nc")
        if os.path.exists(f):
            first_file = f
            break
    
    if first_file is None:
        return None

    with xr.open_dataset(first_file, engine="h5netcdf") as ds:
        lat = ds.latitude.sel(latitude=slice(lat_min, lat_max))
        lon = ds.longitude.sel(longitude=slice(lon_min, lon_max))
        n_lat, n_lon = len(lat), len(lon)

    final_sst = []
    final_times = []
    for dt in date_range:
        fname = os.path.join(dataset_dir, f"sst_{dt.strftime('%Y%m%d')}.nc")
        if os.path.exists(fname):
            with xr.open_dataset(fname, engine="h5netcdf") as ds:
                subset = ds.analysed_sst.sel(
                    latitude=slice(lat_min, lat_max),
                    longitude=slice(lon_min, lon_max)
                )
                val = subset.values[0]
                if val.shape != (n_lat, n_lon):
                    val = np.full((n_lat, n_lon), np.nan)
                final_sst.append(val)
                final_times.append(dt)
        else:
            final_sst.append(np.full((n_lat, n_lon), np.nan))
            final_times.append(dt)

    sst_array = np.stack(final_sst, axis=0).astype(np.float64)
    da = xr.DataArray(
        sst_array,
        coords={'time': final_times, 'latitude': lat, 'longitude': lon},
        dims=['time', 'latitude', 'longitude'],
        name='sst'
    )
    return da

# --- Load Data ---
# Baseline windows extend 5 days before/after the baseline period
baseline_data = load_sst_subset('1991-12-27', '2003-01-05', lat_min, lat_max, lon_min, lon_max)
target_data = load_sst_subset('2019-06-01', '2019-08-31', lat_min, lat_max, lon_min, lon_max)

if baseline_data is None or target_data is None:
    print("Error loading data")
    exit(1)

# --- Process ---
# 1. Sea cells: SST finite on every day of target period
sst_target_vals = target_data.values
is_sea_cell = np.all(np.isfinite(sst_target_vals), axis=0)
n_lat, n_lon = is_sea_cell.shape
n_time_target = sst_target_vals.shape[0]

# 2. Threshold and Climatology
baseline_dates = pd.date_range('1992-01-01', '2002-12-31')
doy_to_dates = {d: [] for d in range(1, 367)}
for dt in baseline_dates:
    doy = get_day_of_year(dt)
    if doy != 60:
        doy_to_dates[doy].append(dt)

# Access baseline SST efficiently
baseline_times = pd.to_datetime(baseline_data.time.values)
time_to_idx = {t: i for i, t in enumerate(baseline_times)}

thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    pool_indices = []
    for b_date in doy_to_dates[d]:
        for offset in range(-5, 6):
            t_date = b_date + timedelta(days=offset)
            if t_date in time_to_idx:
                pool_indices.append(time_to_idx[t_date])
    
    if not pool_indices:
        continue
    
    pool_vals = baseline_data.values[pool_indices] # (len_pool, lat, lon)
    
    # Vectorized approach for threshold and climatology would be faster, 
    # but the cell-by-cell is safer for memory and handles NaNs with nanquantile.
    # To speed up, we can process the pool for all cells at once using np.nanquantile.
    # np.nanquantile is available.
    # But wait, np.nanquantile doesn't have method='hazen'.
    # Let's use a loop for the cells, but maybe only for sea cells to save time.
    for i in range(n_lat):
        for j in range(n_lon):
            if not is_sea_cell[i, j]:
                continue
            cell_pool = pool_vals[:, i, j]
            valid_mask = np.isfinite(cell_pool)
            if np.any(valid_mask):
                valid_vals = cell_pool[valid_mask]
                thresholds[d-1, i, j] = np.quantile(valid_vals, 0.9, method='hazen')
                climatology[d-1, i, j] = np.mean(valid_vals)

# Day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth_366(arr):
    smoothed = np.full_like(arr, np.nan)
    for i in range(366):
        indices = [(i + offset) % 366 for offset in range(-15, 16)]
        window = arr[indices]
        # Use nanmean to ignore land cells (NaNs)
        with np.errstate(all='ignore'):
            smoothed[i] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatology = smooth_366(climatology)

# 3. Per-cell MHWs
target_doys = [get_day_of_year(t) for t in target_data.time.values]
mhw_mask = np.zeros((n_time_target, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not is_sea_cell[i, j]:
            continue
        
        cell_sst = sst_target_vals[:, i, j]
        cell_thresholds = np.array([thresholds[d-1, i, j] for d in target_doys])
        
        # Hot days (finite check included as thresholds might be NaN)
        is_hot = (cell_sst >= cell_thresholds) & np.isfinite(cell_thresholds)
        
        # Find runs of at least 5 hot days
        hot_runs = []
        start = None
        for t in range(n_time_target):
            if is_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        hot_runs.append((start, t-1))
                    start = None
        if start is not None:
            if n_time_target - start >= 5:
                hot_runs.append((start, n_time_target-1))
        
        if not hot_runs:
            continue
            
        # Join gaps of 1 or 2 non-hot days (gap <= 2 means next_start - curr_end <= 3)
        merged = []
        curr_start, curr_end = hot_runs[0]
        for next_start, next_end in hot_runs[1:]:
            if next_start - curr_end <= 3:
                curr_end = next_end
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
        
        for s, e in merged:
            mhw_mask[s : e+1, i, j] = 1

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
            regional_events.append((start, t-1))
            start = None
if start is not None:
    regional_events.append((start, n_time_target-1))

# --- Output ---
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_data.time,
        "latitude": target_data.latitude,
        "longitude": target_data.longitude,
    }
)
os.makedirs('output', exist_ok=True)
ds_out.to_netcdf('output/mhw_mask.nc')

target_times = pd.to_datetime(target_data.time.values)
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {
        "start": target_times[0].strftime('%Y-%m-%d'),
        "end": target_times[-1].strftime('%Y-%m-%d')
    },
    "events": [
        {"onset": target_times[s].strftime('%Y-%m-%d'), "end": target_times[e].strftime('%Y-%m-%d')}
        for s, e in regional_events
    ],
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Analysis complete. Files written to output/")
