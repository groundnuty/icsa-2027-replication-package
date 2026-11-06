import xarray as xr
import numpy as np
import pandas as pd
import os
import json
from datetime import datetime, timedelta

# Constants
LAT_MIN, LAT_MAX = 63.31, 64.51
LON_MIN, LON_MAX = 21.31, 22.51
TARGET_START = '2009-06-01'
TARGET_END = '2009-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'
DIR_PATH = '/data/icsa2027_data_20261101T090944Z/s1z'

def get_files_for_range(start_date, end_date):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    all_files = os.listdir(DIR_PATH)
    sst_files = [f for f in all_files if f.startswith('sst_') and f.endswith('.nc')]
    matching_files = []
    for f in sst_files:
        date_str = f[4:12]
        f_date = pd.to_datetime(date_str, format='%Y%m%d')
        if start <= f_date <= end:
            matching_files.append(f)
    matching_files.sort()
    return matching_files

def load_region_sst(files):
    datasets = []
    for f in files:
        ds = xr.open_dataset(os.path.join(DIR_PATH, f), engine='h5netcdf')
        ds_region = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
        datasets.append(ds_region)
    return xr.concat(datasets, dim='time')

# 1. Load Target Data and Find Sea Cells
target_files = get_files_for_range(TARGET_START, TARGET_END)
ds_target = load_region_sst(target_files)
sst_target = ds_target['analysed_sst'].astype('float64')
is_finite = np.all(np.isfinite(sst_target.values), axis=0)
sea_cells_mask = is_finite

# 2. Threshold and Climatology
# Baseline extended range
b_start_dt = pd.to_datetime(BASELINE_START)
b_end_dt = pd.to_datetime(BASELINE_END)
ext_start = b_start_dt - pd.Timedelta(days=5)
ext_end = b_end_dt + pd.Timedelta(days=5)

baseline_files = get_files_for_range(ext_start.strftime('%Y-%m-%d'), ext_end.strftime('%Y-%m-%d'))
ds_baseline = load_region_sst(baseline_files)
sst_baseline = ds_baseline['analysed_sst'].astype('float64')
time_baseline = sst_baseline.time.values

# We need SST for each cell for each doy
# sst_baseline shape: (time, lat, lon)
# Create a map from date to index
date_to_idx = {t: i for i, t in enumerate(time_baseline)}

# Baseline dates (B)
baseline_dates = pd.date_range(b_start_dt, b_end_dt)

# Pre-calculate pools for each doy (1-366)
# To optimize, we can iterate over doys and find the dates.
thresholds_raw = np.full((367, sst_baseline.latitude.size, sst_baseline.longitude.size), np.nan)
climatology_raw = np.full((367, sst_baseline.latitude.size, sst_baseline.longitude.size), np.nan)

# Iterate over each doy from 1 to 366, skipping 60
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all b in B such that doy(b) == d
    b_dates = [b for b in baseline_dates if b.dayofyear == d]
    
    # The pool for d is the union of [b-5, b+5] for all b in b_dates
    pool_dates = set()
    for b in b_dates:
        for offset in range(-5, 6):
            pool_dates.add(b + pd.Timedelta(days=offset))
    
    # Convert pool_dates to indices
    indices = [date_to_idx[pd.to_datetime(t)] for t in pool_dates if pd.to_datetime(t) in date_to_idx]
    
    if indices:
        # Extract SST for these dates: shape (len(indices), lat, lon)
        pool_sst = sst_baseline.values[indices]
        
        # Compute 90th percentile and mean along the time axis (axis=0)
        # numpy.nanquantile(..., method='hazen')
        thresholds_raw[d] = np.nanquantile(pool_sst, 0.9, axis=0, method='hazen')
        climatology_raw[d] = np.nanmean(pool_sst, axis=0)

# Set day 60 to the mean of 59 and 61
thresholds_raw[60] = (thresholds_raw[59] + thresholds_raw[61]) / 2
climatology_raw[60] = (climatology_raw[59] + climatology_raw[61]) / 2

# Smoothing: 31-day centered moving mean wrapping around
def smooth_366(arr):
    # arr shape: (367, lat, lon) -> we use 1 to 366
    data = arr[1:] # shape (366, lat, lon)
    smoothed = np.full_like(data)
    for d in range(366):
        # Indices for d-15 to d+15 modulo 366
        # d is 0-indexed here, so d=0 corresponds to doy=1
        indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d] = np.nanmean(data[indices], axis=0)
    return smoothed

thresholds_smooth = smooth_366(thresholds_raw)
climatology_smooth = smooth_366(climatology_raw)

# 3. Per-cell MHWs
# Target period SST: sst_target
# target_dates: list of dates
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8) # (time, lat, lon)

# For each cell (lat, lon)
lats = sst_target.latitude.values
lons = sst_target.longitude.values

for i in range(len(lats)):
    for j in range(len(lons)):
        if not sea_cells_mask[i, j]:
            continue
            
        # SST for this cell over target period
        cell_sst = sst_target.values[:, i, j]
        # Thresholds for this cell over target period
        cell_thresholds = []
        for t in target_dates:
            doy = t.dayofyear
            # thresholds_smooth is 0-indexed (doy 1 is index 0)
            cell_thresholds.append(thresholds_smooth[doy - 1, i, j])
        cell_thresholds = np.array(cell_thresholds)
        
        # Hot days: SST >= threshold
        hot = cell_sst >= cell_thresholds
        
        # Find runs of at least 5 consecutive hot days
        # and join gaps of 1 or 2 non-hot days
        n_days = len(hot)
        in_mhw = np.zeros(n_days, dtype=bool)
        
        # Initial hot runs
        runs = []
        start = None
        for d in range(n_days):
            if hot[d]:
                if start is None:
                    start = d
            else:
                if start is not None:
                    if d - start >= 5:
                        runs.append((start, d - 1))
                    start = None
        if start is not None:
            if n_days - start >= 5:
                runs.append((start, n_days - 1))
        
        # Join gaps
        if runs:
            merged = []
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                gap = next_start - curr_end - 1
                if gap <= 2:
                    curr_end = next_end
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
            
            for s, e in merged:
                in_mhw[s : e + 1] = True
        
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# 4. Regional Events
# A day is active if at least one sea cell is in an MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))

# Regional MHW events: maximal runs of consecutive active days
regional_events = []
start = None
for d in range(len(active_days)):
    if active_days[d]:
        if start is None:
            start = d
    else:
        if start is not None:
            regional_events.append((target_dates[start], target_dates[d-1]))
            start = None
if start is not None:
    regional_events.append((target_dates[start], target_dates[-1]))

# Format results
onset_end_events = [{"onset": e[0].strftime('%Y-%m-%d'), "end": e[1].strftime('%Y-%m-%d')} for e in regional_events]

# Write output
os.makedirs('output', exist_ok=True)
# mhw_mask.nc
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_dates, "latitude": lats, "longitude": lons}
)
ds_out.to_netcdf('output/mhw_mask.nc')

# report.json
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": ext_start.strftime('%Y-%m-%d'), "end": ext_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": onset_end_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Done")
