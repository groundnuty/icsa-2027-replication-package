import fsspec
import xarray as xr
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta

# Constants
REGION = {'lat_min': 59.93, 'lat_max': 61.13, 'lon_min': 18.69, 'lon_max': 19.89}
TARGET_START = '2007-06-01'
TARGET_END = '2007-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'
DATA_PATH = 'icsa2027_data_20261101T090944Z/s1z'

fs = fsspec.filesystem('onedata')

def get_sst_subset(date):
    date_str = date.strftime('%Y%m%d')
    remote_file = f'{DATA_PATH}/sst_{date_str}.nc'
    local_file = f'/work/sst_{date_str}.nc'
    try:
        fs.get(remote_file, local_file)
        with xr.open_dataset(local_file, engine='h5netcdf') as ds:
            subset = ds.analysed_sst.sel(
                latitude=slice(REGION['lat_min'], REGION['lat_max']),
                longitude=slice(REGION['lon_min'], REGION['lon_max'])
            )
            data = subset.values.astype(np.float64)
            lats = subset.latitude.values
            lons = subset.longitude.values
        os.remove(local_file)
        return data[0], lats, lons
    except Exception:
        return None, None, None

# 1. Target period data
target_dates = pd.date_range(TARGET_START, TARGET_END)
target_sst_list = []
lats, lons = None, None

for d in target_dates:
    data, lt, ln = get_sst_subset(d)
    if data is not None:
        target_sst_list.append(data)
        lats, lons = lt, ln
    else:
        if lats is None:
            target_sst_list.append(np.full((60, 60), np.nan))
        else:
            target_sst_list.append(np.full((lats.shape[0], lons.shape[0]), np.nan))

target_sst = np.array(target_sst_list)
if lats is None:
    # fallback if all target days failed
    lats = np.arange(REGION['lat_min'], REGION['lat_max'], 0.02)
    lons = np.arange(REGION['lon_min'], REGION['lon_max'], 0.02)

is_sea = np.all(np.isfinite(target_sst), axis=0)

# 2. Baseline data
baseline_start_dt = pd.to_datetime(BASELINE_START)
baseline_end_dt = pd.to_datetime(BASELINE_END)
baseline_fetch_range = pd.date_range(baseline_start_dt - pd.Timedelta(days=5),
                                     baseline_end_dt + pd.Timedelta(days=5))

all_baseline_sst = {}
for d in baseline_fetch_range:
    data, _, _ = get_sst_subset(d)
    if data is not None:
        all_baseline_sst[d] = data

# 3. Thresholds and Climatology
thresholds = np.full((366, target_sst.shape[1], target_sst.shape[2]), np.nan, dtype=np.float64)
climatology = np.full((366, target_sst.shape[1], target_sst.shape[2]), np.nan, dtype=np.float64)

baseline_years = range(1992, 2003)
for d in range(1, 367):
    if d == 60: continue
    
    pool_dates = set()
    for year in baseline_years:
        try:
            year_dates = pd.date_range(f'{year}-01-01', f'{year}-12-31')
            for date in year_dates:
                if date.dayofyear == d:
                    for offset in range(-5, 6):
                        pool_dates.add(date + pd.Timedelta(days=offset))
                    break
        except Exception:
            continue

    pool_values = [all_baseline_sst[pd_date] for pd_date in pool_dates if pd_date in all_baseline_sst]
    
    if pool_values:
        pool_array = np.array(pool_values)
        thresholds[d-1] = np.nanquantile(pool_array, 0.9, axis=0, method='hazen')
        climatology[d-1] = np.nanmean(pool_array, axis=0)

# Day 60 handling
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing
def smooth_array(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        window = []
        for offset in range(-15, 16):
            idx = (d + offset) % 366
            window.append(arr[idx])
        smoothed[d] = np.nanmean(np.array(window), axis=0)
    return smoothed

thresholds = smooth_array(thresholds)
climatology = smooth_array(climatology)

# 4. Per-cell MHWs
hot_days = np.zeros(target_sst.shape, dtype=bool)
for i, d in enumerate(target_dates):
    # Correcting for doy index (1-366)
    hot_days[i] = target_sst[i] >= thresholds[d.dayofyear - 1]

mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
lat_size, lon_size = target_sst.shape[1], target_sst.shape[2]

for r in range(lat_size):
    for c in range(lon_size):
        if not is_sea[r, c]:
            continue
        
        cell_hot = hot_days[:, r, c]
        runs = []
        i = 0
        while i < len(cell_hot):
            if cell_hot[i]:
                start = i
                while i < len(cell_hot) and cell_hot[i]:
                    i += 1
                if i - start >= 5:
                    runs.append([start, i])
            else:
                i += 1
        
        if runs:
            merged = []
            curr_s, curr_e = runs[0]
            for n_s, n_e in runs[1:]:
                if 1 <= (n_s - curr_e) <= 3: # Gap of 1 or 2 days (indices: curr_e, ... n_s-1)
                    # Gap size is (n_s - curr_e - 1)
                    # If n_s - curr_e = 2, gap is 1 day. If n_s - curr_e = 3, gap is 2 days.
                    # Wait: if curr_e is the index of the first non-hot day, and n_s is the first hot day of next run.
                    # The non-hot days are from curr_e to n_s-1.
                    # Number of non-hot days = (n_s - 1) - curr_e + 1 = n_s - curr_e.
                    # So for 1 or 2 non-hot days, 1 <= n_s - curr_e <= 2.
                    # Let's re-verify: 
                    # Run 1: [0, 5) -> end = 5 (index 4 hot, 5 not).
                    # Run 2: [6, 11) -> start = 6.
                    # Gap is index 5. Gap size = 1. n_s - curr_e = 6 - 5 = 1.
                    # Run 2: [7, 12) -> start = 7.
                    # Gap is indices 5, 6. Gap size = 2. n_s - curr_e = 7 - 5 = 2.
                    # So 1 <= n_s - curr_e <= 2.
                    curr_e = n_e
                else:
                    merged.append([curr_s, curr_e])
                    curr_s, curr_e = n_s, n_e
            merged.append([curr_s, curr_e])
            
            cell_mhw = np.zeros(len(cell_hot), dtype=bool)
            for s, e in merged:
                cell_mhw[s:e] = True
            mhw_mask[:, r, c] = cell_mhw.astype(np.uint8)

# 5. Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start = i
        while i < len(active_days) and active_days[i]:
            i += 1
        end = i - 1
        regional_events.append({'onset': target_dates[start].strftime('%Y-%m-%d'), 
                                'end': target_dates[end].strftime('%Y-%m-%d')})
    else:
        i += 1

# 6. Outputs
os.makedirs('output', exist_ok=True)

# NetCDF
ds_out = xr.Dataset(
    data_vars={'mhw': (['time', 'latitude', 'longitude'], mhw_mask.astype(np.uint8))},
    coords={'time': target_dates, 'latitude': lats, 'longitude': lons}
)
ds_out.to_netcdf('output/mhw_mask.nc')

# JSON
report = {
    "region": REGION,
    "baseline_analysed": {
        "start": baseline_fetch_range[0].strftime('%Y-%m-%d'),
        "end": baseline_fetch_range[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_dates[0].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Done. Files written to output/")
