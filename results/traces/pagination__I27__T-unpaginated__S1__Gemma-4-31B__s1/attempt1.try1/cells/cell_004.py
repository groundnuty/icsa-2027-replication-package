import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

# Region bounds
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

# Date ranges
# Pool can extend from 1991-12-27 to 2003-01-05
pool_start = pd.Timestamp('1991-12-27')
pool_end = pd.Timestamp('2003-01-05')
target_start = pd.Timestamp('2008-06-01')
target_end = pd.Timestamp('2008-08-31')

def get_date_from_filename(filename):
    date_str = filename.split('/')[-1].split('_')[1].split('.')[0]
    return pd.Timestamp(date_str)

all_files = fs.ls(base_path)

pool_files = []
for f in all_files:
    dt = get_date_from_filename(f)
    if pool_start <= dt <= pool_end:
        pool_files.append(f)
pool_files.sort()

target_files = []
for f in all_files:
    dt = get_date_from_filename(f)
    if target_start <= dt <= target_end:
        target_files.append(f)
target_files.sort()

def load_region(files):
    datasets = []
    for f in files:
        with fs.open(f, "rb") as site_g:
            ds = xr.open_dataset(site_g, engine="h5netcdf")
            ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            datasets.append(ds_reg)
    return xr.concat(datasets, dim='time')

ds_pool = load_region(pool_files)
ds_target = load_region(target_files)

# Use float64 for calculations
sst_pool = ds_pool['analysed_sst'].astype(np.float64)
sst_target = ds_target['analysed_sst'].astype(np.float64)

def get_day_of_year(dt):
    month = dt.month
    day = dt.day
    month_days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:month]) + day
    if month > 2:
        doy += 1
    return doy

# Target period days
target_dates = pd.to_datetime(ds_target.time.values)
# Baseline period dates
baseline_dates = pd.date_range(start='1992-01-01', end='2002-12-31')

# 1. Sea cells: SST is finite on every day of target period
# Target SST shape: (time, lat, lon)
finite_mask = np.all(np.isfinite(sst_target), axis=0)
sea_cells = finite_mask # Boolean array (lat, lon)

# 2. Threshold and Climatology
# We need this for each sea cell and day of year
n_lat = sst_target.shape[1]
n_lon = sst_target.shape[2]
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

# Pre-calculate DOY for all dates in ds_pool
pool_dates = pd.to_datetime(ds_pool.time.values)
pool_doy = np.array([get_day_of_year(d) for d in pool_dates])

# For each baseline date D in [1992-01-01, 2002-12-31]
# This is a bit slow if we loop over D and then over d.
# Let's optimize: for each d, find all D with DOY(D)=d, then find all dates in pool within ±5 days.
for d in range(1, 367):
    if d == 60:
        continue
    
    # Baseline dates D with DOY(D) = d
    baseline_dates_with_d = [D for D in baseline_dates if get_day_of_year(D) == d]
    
    # All dates in pool within ±5 days of any such D
    pool_indices = []
    for D in baseline_dates_with_d:
        # Find indices in pool_dates that are within ±5 days of D
        # pool_dates is sorted
        start_win = D - pd.Timedelta(days=5)
        end_win = D + pd.Timedelta(days=5)
        
        # Use searchsorted for efficiency
        idx_start = np.searchsorted(pool_dates, start_win)
        idx_end = np.searchsorted(pool_dates, end_win, side='right')
        pool_indices.extend(range(idx_start, idx_end))
    
    unique_pool_indices = sorted(list(set(pool_indices)))
    
    if not unique_pool_indices:
        continue
        
    # Extract SST values for these indices: (len(unique_pool_indices), lat, lon)
    pool_sst = sst_pool.values[unique_pool_indices, :, :]
    
    # Compute 90th percentile and mean along axis 0, ignoring NaN
    # np.nanquantile and np.nanmean
    thresholds[d-1] = np.nanquantile(pool_sst, 0.9, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool_sst, axis=0)

# Handle day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day centred moving mean, wrap around
def smooth_366(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for d in range(366):
        # Window: d-15 to d+15 (modulo 366)
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatologies = smooth_366(climatologies)

# 3. Per-cell MHWs
# Target period: 2008-06-01 to 2008-08-31
# SST is sst_target (time, lat, lon)
target_doy = np.array([get_day_of_year(d) for d in target_dates])

# Hot days: SST >= threshold for that day of year
# thresholds shape (366, lat, lon), target_doy shape (time,)
# Need to expand target_doy to index thresholds
hot_mask = np.zeros(sst_target.shape, dtype=bool)
for t in range(len(target_dates)):
    d = target_doy[t]
    hot_mask[t, :, :] = sst_target.values[t, :, :] >= thresholds[d-1, :, :]

# Find per-cell MHWs
# a run of at least 5 consecutive hot days
# joined by gaps of 1 or 2 non-hot days
mhw_mask = np.zeros(sst_target.shape, dtype=uint8 if 'uint8' in globals() else np.uint8)
# Note: uint8 is not defined, use np.uint8

# Loop over each sea cell
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        # Hot days for this cell
        cell_hot = hot_mask[:, i, j]
        cell_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        # Find runs of >= 5 hot days
        # A simple way to find runs:
        runs = []
        start = None
        for t in range(len(cell_hot)):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append((start, t - 1))
                    start = None
        if start is not None:
            if len(cell_hot) - start >= 5:
                runs.append((start, len(cell_hot) - 1))
        
        # Now join runs with gaps of 1 or 2
        if not runs:
            continue
            
        merged_runs = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            if next_start - curr_end - 1 <= 2:
                curr_end = next_end
            else:
                merged_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged_runs.append((curr_start, curr_end))
        
        for start, end in merged_runs:
            cell_mhw[start:end+1] = True
        
        mhw_mask[:, i, j] = cell_mhw.astype(np.uint8)

# 4. Regional events
# a day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))

regional_events = []
event_start = None
for t in range(len(active_days)):
    if active_days[t]:
        if event_start is None:
            event_start = t
    else:
        if event_start is not None:
            regional_events.append((target_dates[event_start], target_dates[t-1]))
            event_start = None
if event_start is not None:
    regional_events.append((target_dates[event_start], target_dates[-1]))

# Write output files
os.makedirs('output', exist_ok=True)

# output/mhw_mask.nc
mhw_ds = xr.Dataset(
    {'mhw': (('time', 'latitude', 'longitude'), mhw_mask)},
    coords={
        'time': ds_target.time,
        'latitude': ds_target.latitude,
        'longitude': ds_target.longitude
    }
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

# output/report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": [{"onset": e[0].strftime('%Y-%m-%d'), "end": e[1].strftime('%Y-%m-%d')} for e in regional_events],
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Done")
