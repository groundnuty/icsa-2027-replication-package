import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
import os

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

# Region bounds
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

# Date ranges
pool_start = pd.Timestamp('1991-12-27')
pool_end = pd.Timestamp('2003-01-05')
target_start = pd.Timestamp('2008-06-01')
target_end = pd.Timestamp('2008-08-31')

def get_date_from_filename(filename):
    date_str = filename.split('/')[-1].split('_')[1].split('.')[0]
    return pd.Timestamp(date_str)

def is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def get_custom_doy(dt):
    doy = dt.timetuple().tm_yday
    if dt.month >= 3 and not is_leap(dt.year):
        doy += 1
    return doy

all_files = fs.ls(base_path)

pool_files = sorted([f for f in all_files if pool_start <= get_date_from_filename(f) <= pool_end])
target_files = sorted([f for f in all_files if target_start <= get_date_from_filename(f) <= target_end])

def load_region_data(files):
    data_list = []
    times = []
    lats, lons = None, None
    for f in files:
        with fs.open(f, "rb") as site_g:
            ds = xr.open_dataset(site_g, engine="h5netcdf")
            ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            data_list.append(ds_reg['analysed_sst'].values.astype(np.float64))
            times.append(ds_reg.time.values)
            if lats is None:
                lats = ds_reg.latitude.values
                lons = ds_reg.longitude.values
    return np.concatenate(data_list, axis=0), np.concatenate(times, axis=0), lats, lons

sst_pool_vals, pool_times, lats, lons = load_region_data(pool_files)
sst_target_vals, target_times, _, _ = load_region_data(target_files)

# 1. Sea cells: SST is finite on every day of target period
finite_mask = np.all(np.isfinite(sst_target_vals), axis=0)
sea_cells = finite_mask

# 2. Threshold and Climatology
n_lat, n_lon = sst_target_vals.shape[1:]
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

baseline_dates = pd.date_range(start='1992-01-01', end='2002-12-31')
pool_dates = pd.to_datetime(pool_times)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Baseline dates D with DOY(D) = d
    baseline_dates_with_d = [D for D in baseline_dates if get_custom_doy(D) == d]
    
    pool_indices = []
    for D in baseline_dates_with_d:
        start_win = D - pd.Timedelta(days=5)
        end_win = D + pd.Timedelta(days=5)
        idx_start = np.searchsorted(pool_dates, start_win)
        idx_end = np.searchsorted(pool_dates, end_win, side='right')
        pool_indices.extend(range(idx_start, idx_end))
    
    unique_pool_indices = sorted(list(set(pool_indices)))
    if not unique_pool_indices:
        continue
        
    pool_sst = sst_pool_vals[unique_pool_indices, :, :]
    thresholds[d-1] = np.nanquantile(pool_sst, 0.9, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool_sst, axis=0)

# Day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing
def smooth_366(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatologies = smooth_366(climatologies)

# 3. Per-cell MHWs
target_dates = pd.to_datetime(target_times)
target_doy = np.array([get_custom_doy(d) for d in target_dates])

hot_mask = np.zeros(sst_target_vals.shape, dtype=bool)
for t in range(len(target_dates)):
    d = target_doy[t]
    hot_mask[t, :, :] = sst_target_vals[t, :, :] >= thresholds[d-1, :, :]

mhw_mask = np.zeros(sst_target_vals.shape, dtype=np.uint8)
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        cell_hot = hot_mask[:, i, j]
        cell_mhw = np.zeros(len(cell_hot), dtype=bool)
        
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

# Write output
os.makedirs('output', exist_ok=True)
mhw_ds = xr.Dataset(
    {'mhw': (('time', 'latitude', 'longitude'), mhw_mask)},
    coords={'time': target_times, 'latitude': lats, 'longitude': lons}
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

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
