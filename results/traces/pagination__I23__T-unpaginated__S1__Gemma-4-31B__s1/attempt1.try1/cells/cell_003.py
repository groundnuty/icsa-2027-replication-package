import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 57.41, 58.61
lon_min, lon_max = 18.69, 19.89
target_start_str = '2013-06-01'
target_end_str = '2013-08-31'
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'

target_start = pd.to_datetime(target_start_str)
target_end = pd.to_datetime(target_end_str)
baseline_start = pd.to_datetime(baseline_start_str)
baseline_end = pd.to_datetime(baseline_end_str)

# We need SST for baseline windows and target period
# Baseline window: [baseline_start - 5 days, baseline_end + 5 days]
pool_start = baseline_start - pd.Timedelta(days=5)
pool_end = baseline_end + pd.Timedelta(days=5)

all_files = fs.ls(base_path)
relevant_files = []
for f in all_files:
    date_str = f.split('_')[-1].replace('.nc', '')
    f_date = pd.to_datetime(date_str)
    if (pool_start <= f_date <= pool_end) or (target_start <= f_date <= target_end):
        relevant_files.append(f)
relevant_files.sort()

def get_doy(date):
    return date.dayofyear

# 1. Find sea cells
# Load SST for the target period to check finiteness
target_files = [f for f in relevant_files if target_start <= pd.to_datetime(f.split('_')[-1].replace('.nc', '')) <= target_end]
target_sst_list = []
for f in target_files:
    with fs.open(f, "rb") as f_obj:
        ds = xr.open_dataset(f_obj, engine="h5netcdf")
        # Subset region immediately to save memory
        ds_sub = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
        target_sst_list.append(ds_sub.analysed_sst)

target_sst = xr.concat(target_sst_list, dim='time').astype(np.float64)

# Identify sea cells: SST finite on every day of the target period
# target_sst has dims (time, latitude, longitude)
# finite = np.isfinite(target_sst)
# sea_mask = finite.all(dim='time')
sea_mask = np.isfinite(target_sst).all(axis=0)

# 2. Compute Threshold and Climatology
# Pre-load baseline SST in the region
baseline_files = [f for f in relevant_files if pool_start <= pd.to_datetime(f.split('_')[-1].replace('.nc', '')) <= pool_end]
baseline_sst_list = []
baseline_dates = []
for f in baseline_files:
    date_str = f.split('_')[-1].replace('.nc', '')
    baseline_dates.append(pd.to_datetime(date_str))
    with fs.open(f, "rb") as f_obj:
        ds = xr.open_dataset(f_obj, engine="h5netcdf")
        ds_sub = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
        baseline_sst_list.append(ds_sub.analysed_sst)

baseline_sst = xr.concat(baseline_sst_list, dim='time').astype(np.float64)
baseline_time = xr.DataArray(baseline_dates, dim='time')

# Mapping and Pool logic
# We need thresholds and climatology for each sea cell for each DOY 1-366.
# Use only sea cells to save computations.
lats = target_sst.latitude.values
lons = target_sst.longitude.values
n_lat = len(lats)
n_lon = len(lons)

thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

# Baseline dates: 1992-01-01 to 2002-12-31
# Find dates in the baseline range and their DOYs
baseline_range_dates = pd.date_range(baseline_start, baseline_end)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all dates T in baseline_range_dates with DOY == d
    # Then find all dates within T +/- 5 days that exist in baseline_sst's time.
    pool_dates = []
    for T in baseline_range_dates:
        if T.dayofyear == d:
            # Window [T-5, T+5]
            for delta in range(-5, 6):
                pool_dates.append(T + pd.Timedelta(days=delta))
    
    # Find indices of these dates in baseline_time
    # To be efficient, use a set or map
    time_map = {t: i for i, t in enumerate(baseline_time.values)}
    indices = [time_map[t] for t in pool_dates if t in time_map]
    
    if not indices:
        continue
    
    # Extract SST values for the pool
    # baseline_sst is (time, lat, lon)
    # pool_sst is (len(indices), lat, lon)
    pool_sst = baseline_sst.values[indices] # (N, lat, lon)
    
    # Compute 90th percentile and mean across the N dimension
    # Numpy's quantile method="hazen" is Hyndman-Fan type 5
    # We need to ignore NaNs. np.nanquantile.
    # Since we only care about sea cells, we can do it for all and then mask, 
    # but doing it for all might be slow.
    
    # For each cell, compute stats
    # We can reshape to (N, n_lat * n_lon)
    reshaped_pool = pool_sst.reshape(len(indices), -1)
    
    # Using np.nanquantile is slow. Let's try to optimize.
    # We only need to do this for sea cells.
    # But we can just do it and it will be NaN for land cells anyway.
    
    q90 = np.nanquantile(reshaped_pool, 0.9, axis=0, method='hazen')
    mean_val = np.nanmean(reshaped_pool, axis=0)
    
    thresholds[d-1] = q90.reshape(n_lat, n_lon)
    climatologies[d-1] = mean_val.reshape(n_lat, n_lon)

# Day 60 logic
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day moving mean, wrap around
def smooth(arr):
    # arr is (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for d in range(366):
        # d-15 to d+15 modulo 366
        indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d] = np.nanmean(arr[indices], axis=0)
    return smoothed

thresholds = smooth(thresholds)
climatologies = smooth(climatologies)

# 3. Per-cell MHWs
# target_sst is (time, lat, lon)
# target_time = target_files' dates
target_dates = pd.to_datetime([f.split('_')[-1].replace('.nc', '') for f in target_files])
target_doys = np.array([d.dayofyear for d in target_dates])

# hot_mask: (time, lat, lon)
hot_mask = np.zeros(target_sst.shape, dtype=bool)
for t in range(len(target_dates)):
    doy = target_doys[t]
    # DOY 60 is handled by the smooth/mean already
    hot_mask[t] = target_sst.values[t] >= thresholds[doy-1]

# Per-cell MHW detection
mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        
        cell_hot = hot_mask[:, i, j]
        # Find runs of at least 5 hot days
        # Join gaps of 1-2 non-hot days
        
        # 1. Find runs of hot days
        is_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        # Initial runs
        runs = []
        start = None
        for t in range(len(cell_hot)):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append([start, t-1])
                    start = None
        if start is not None:
            if len(cell_hot) - start >= 5:
                runs.append([start, len(cell_hot)-1])
        
        # 2. Join gaps of 1 or 2
        if not runs:
            continue
            
        merged_runs = []
        if runs:
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    merged_runs.append([curr_start, curr_end])
                    curr_start, curr_end = next_start, next_end
            merged_runs.append([curr_start, curr_end])
            
        for start, end in merged_runs:
            mhw_mask[start:end+1, i, j] = 1

# 4. Regional events
# active_days: (time,)
active_days = np.any(mhw_mask == 1, axis=(1, 2))

regional_events = []
start = None
for t in range(len(active_days)):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append({
                "onset": target_dates[start].strftime('%Y-%m-%d'),
                "end": target_dates[t-1].strftime('%Y-%m-%d')
            })
            start = None
if start is not None:
    regional_events.append({
        "onset": target_dates[start].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    })

# Output files
os.makedirs('output', exist_ok=True)

# mhw_mask.nc
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_dates, "latitude": lats, "longitude": lons}
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": pool_start.strftime('%Y-%m-%d'),
        "end": pool_end.strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_start.strftime('%Y-%m-%d'),
        "end": target_end.strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Analysis complete. Files written.")
