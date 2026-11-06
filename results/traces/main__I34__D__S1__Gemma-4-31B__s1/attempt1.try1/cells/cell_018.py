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
            time = subset.time.values
        os.remove(local_file)
        return data[0], lats, lons, time
    except Exception as e:
        print(f"Error loading {date_str}: {e}")
        return None, None, None, None

# 1. Target period data
target_dates = pd.date_range(TARGET_START, TARGET_END)
target_sst_list = []
lats, lons, times = None, None, None

print("Fetching target period data...")
for d in target_dates:
    data, lt, ln, tm = get_sst_subset(d)
    if data is None:
        # In case of missing data, we should be careful. 
        # But for this task, we assume data exists if the method says so.
        # For now, let's just append NaNs if a day is missing.
        target_sst_list.append(np.full((60, 60), np.nan)) # Shape assumption, will fix
    else:
        target_sst_list.append(data)
        lats, lons, times = lt, ln, tm

target_sst = np.array(target_sst_list) # (days, lat, lon)
print(f"Target SST shape: {target_sst.shape}")

# 2. Sea cells: finite on every day of target period
# A cell is sea if all its target SST values are finite.
is_sea = np.all(np.isfinite(target_sst), axis=0)
sea_cells_count = np.sum(is_sea)
print(f"Sea cells: {sea_cells_count} / {is_sea.size}")

# 3. Baseline data and thresholds
# Baseline: 1992-01-01 to 2002-12-31
# Buffer: +/- 5 days
baseline_dates_range = pd.date_range(
    pd.to_datetime(BASELINE_START) - pd.Timedelta(days=5),
    pd.to_datetime(BASELINE_END) + pd.Timedelta(days=5)
)

# Map dates to Day of Year (DOY)
def get_doy(date):
    # 1 Jan = 1, 29 Feb = 60, 1 Mar = 61
    # pandas .dayofyear does exactly this.
    return date.dayofyear

# Collect SSTs for baseline dates
baseline_data_dict = {} # doy -> list of (lat, lon) arrays
print("Fetching baseline data...")
for d in baseline_dates_range:
    data, _, _, _ = get_sst_subset(d)
    if data is not None:
        doy = get_doy(d)
        if doy not in baseline_data_dict:
            baseline_data_dict[doy] = []
        baseline_data_dict[doy].append(data)

# Threshold and Climatology
# Threshold is 90th percentile, Climatology is mean.
# Per cell, per doy.
# Day 60 handled separately.
# Window: +/- 5 calendar days of baseline dates of that doy.

# Baseline dates in the 1992-2002 period
baseline_years = range(1992, 2003)
baseline_calendar_dates = pd.date_range(BASELINE_START, BASELINE_END)

# Pre-calculate the pools for each doy (1 to 366)
# For each doy d (excluding 60), pool = all values within +/- 5 days of any baseline date with doy d.
thresholds = np.full((366, target_sst.shape[1], target_sst.shape[2]), np.nan, dtype=np.float64)
climatology = np.full((366, target_sst.shape[1], target_sst.shape[2]), np.nan, dtype=np.float64)

# Optimizing: first, gather all baseline SSTs into a structured array or dict
all_baseline_sst = {} # date -> data
for d in baseline_dates_range:
    data, _, _, _ = get_sst_subset(d)
    if data is not None:
        all_baseline_sst[d] = data

print("Computing thresholds and climatology...")
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all baseline dates in 1992-2002 that have doy == d
    # Then for each such date, take window [date-5, date+5]
    pool_dates = set()
    for year in baseline_years:
        try:
            # Try to find the date with doy d in this year
            # Handling leap years: if d=60 and year is not leap, this fails.
            # If d > 60 and year is not leap, the date is actually doy d-1.
            # Easiest: check all dates in the year.
            year_dates = pd.date_range(f'{year}-01-01', f'{year}-12-31')
            for date in year_dates:
                if date.dayofyear == d:
                    # Add window
                    for offset in range(-5, 6):
                        pool_dates.add(date + pd.Timedelta(days=offset))
                    break
        except Exception:
            continue
            
    # Extract values for these dates
    pool_values = []
    for pd_date in pool_dates:
        if pd_date in all_baseline_sst:
            pool_values.append(all_baseline_sst[pd_date])
    
    if pool_values:
        pool_array = np.array(pool_values) # (n_days, lat, lon)
        
        # For each cell (lat, lon)
        # We only care about sea cells, but we can compute for all
        # numpy.nanquantile and numpy.nanmean
        # Note: numpy.nanquantile does not have method='hazen' (which is type 5).
        # Hyndman-Fan type 5: (i-1)/(n-1)
        # In numpy, quantile method='hazen' exists since 1.22.0
        # If available, it should match MATLAB's default.
        
        # To avoid slow loops, we use nanpercentile/nanmean along the 0-axis
        thresholds[d-1] = np.nanquantile(pool_array, 0.9, axis=0, method='hazen')
        climatology[d-1] = np.nanmean(pool_array, axis=0)

# Handle Day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smooth: 31-day moving mean, wrap around
def smooth(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        window = []
        for offset in range(-15, 16):
            idx = (d + offset) % 366
            window.append(arr[idx])
        smoothed[d] = np.nanmean(np.array(window), axis=0)
    return smoothed

print("Smoothing...")
thresholds = smooth(thresholds)
climatology = smooth(climatology)

# 4. MHW detection
# target_sst: (days, lat, lon)
# thresholds: (366, lat, lon)
# target_dates: (days,)

hot_days = np.zeros(target_sst.shape, dtype=bool)
for i, d in enumerate(target_dates):
    doy = d.dayofyear
    # thresholds is 0-indexed, so doy-1
    hot_days[i] = target_sst[i] >= thresholds[doy-1]

# MHWs per cell: run of >= 5 hot days, join gaps of 1-2 days
mhw_mask = np.zeros(target_sst.shape, dtype=uint8)
# We need to process each cell individually
lat_size, lon_size = target_sst.shape[1], target_sst.shape[2]
mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)

for r in range(lat_size):
    for c in range(lon_size):
        if not is_sea[r, c]:
            continue
        
        cell_hot = hot_days[:, r, c]
        # Find runs
        cell_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        # Basic run detection
        i = 0
        while i < len(cell_hot):
            if cell_hot[i]:
                start = i
                while i < len(cell_hot) and cell_hot[i]:
                    i += 1
                end = i # exclusive
                if end - start >= 5:
                    cell_mhw[start:end] = True
            else:
                i += 1
        
        # Join gaps (1 or 2 non-hot days)
        # Repeat until no more joins
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(cell_hot) - 2:
                # Gap of 1
                if not cell_mhw[i] and cell_mhw[i-1] and cell_mhw[i+1]:
                    cell_mhw[i] = True
                    changed = True
                # Gap of 2
                elif not cell_mhw[i] and not cell_mhw[i+1] and (i>0 and cell_mhw[i-1]) and (i+2 < len(cell_hot) and cell_mhw[i+2]):
                    cell_mhw[i] = True
                    cell_mhw[i+1] = True
                    changed = True
                i += 1
        
        # Wait, the join logic is: "per-cell MHWs separated by 1 or 2 non-hot days are joined"
        # My logic above is a bit simplistic. Let's refine it.
        # Correct logic: Find all initial MHWs (runs >= 5). Then if two such MHWs are separated by 1 or 2 days, join them.
        
        # Re-doing cell MHW logic
        cell_mhw = np.zeros(len(cell_hot), dtype=bool)
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
        
        # Join runs
        if runs:
            merged = []
            current_start, current_end = runs[0]
            for next_start, next_end in runs[1:]:
                if next_start - current_end <= 3: # gap of 1 or 2 days means next_start - current_end is 2 or 3
                    # Wait: current_end is the first non-hot day.
                    # Gap of 1: current_end is the only gap day. next_start = current_end + 1.
                    # Gap of 2: current_end and current_end + 1 are gap days. next_start = current_end + 2.
                    # So gap is (next_start - current_end - 1).
                    # 1 or 2 non-hot days: next_start - current_end - 1 <= 2 => next_start - current_end <= 3.
                    # Let's check: 
                    # end=10 (idx 9 is hot, idx 10 is not), start=11 (idx 11 is hot) -> gap = 11-10-1 = 0. No.
                    # end=10 (idx 9 hot, idx 10 not), start=12 (idx 12 hot) -> gap = 12-10-1 = 1. Correct.
                    # end=10 (idx 9 hot, idx 10 not), start=13 (idx 13 hot) -> gap = 13-10-1 = 2. Correct.
                    # So gap is next_start - current_end. If next_start - current_end == 1, gap is 0. 
                    # If next_start - current_end == 2, gap is 1 day (index current_end).
                    # If next_start - current_end == 3, gap is 2 days (indices current_end, current_end+1).
                    # So gap 1 or 2 means 2 <= next_start - current_end <= 3.
                    # Actually, if they are adjacent (next_start == current_end), they are the same run.
                    # If next_start - current_end == 1, they are separated by 0 non-hot days (which is impossible if we found runs).
                    # So if 1 <= next_start - current_end <= 3, join them.
                    current_end = next_end
                else:
                    merged.append([current_start, current_end])
                    current_start, current_end = next_start, next_end
            merged.append([current_start, current_end])
            for start, end in merged:
                cell_mhw[start:end] = True
        
        mhw_mask[:, r, c] = cell_mhw.astype(np.uint8)

# 5. Regional Events
# a day is active if at least one sea cell is in an MHW
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

# 6. Final outputs
# mhw_mask.nc
# report.json
