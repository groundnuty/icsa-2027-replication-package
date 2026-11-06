import xarray as xr
import fsspec
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

def get_doy_custom(dt):
    month = dt.month
    day = dt.day
    month_starts = {
        1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151, 
        7: 181, 8: 212, 9: 243, 10: 273, 11: 304, 12: 334
    }
    if month == 2 and day == 29:
        return 60
    if month <= 2:
        return month_starts[month] + day
    else:
        return month_starts[month] + day + 1

# Parameters
lat_min, lat_max = 57.13, 58.33
lon_min, lon_max = 22.79, 23.99
target_start = "2014-06-01"
target_end = "2014-08-31"
baseline_start = "1992-01-01"
baseline_end = "2002-12-31"

# Extended baseline for windows
baseline_ext_start = "1991-12-27"
baseline_ext_end = "2003-01-05"

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    # Use chunks to handle memory if needed, though the region is small
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Subset region
    region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Baseline data
    baseline_ds = region_ds.sel(time=slice(baseline_ext_start, baseline_ext_end))
    
    # Target data
    target_ds = region_ds.sel(time=slice(target_start, target_end))

# Sea cells: SST is finite on every day of the target period
sst_target = target_ds['analysed_sst'].astype(np.float64)
# Finite on all target days (axis=0 is time)
is_sea = np.all(np.isfinite(sst_target.values), axis=0)

# Subset further to sea cells
# We'll keep all cells for the mask, but only calculate MHWs for sea cells
# Let's get the SST for sea cells
# sst_target_sea = sst_target.where(is_sea) # Not needed yet

# Now we process per sea cell
# To optimize, we can work with the numpy array for baseline
sst_baseline = baseline_ds['analysed_sst'].astype(np.float64)
# Get time indices for baseline
baseline_times = pd.to_datetime(sst_baseline.time.values)

# We need to calculate threshold and climatology for each cell and each doy 1-366
# Doy mapping for the baseline dataset
baseline_doys = np.array([get_doy_custom(t) for t in baseline_times])

# We will store these as arrays (lat, lon, doy)
n_lat = region_ds.latitude.size
n_lon = region_ds.longitude.size
thresholds = np.full((n_lat, n_lon, 367), np.nan, dtype=np.float64) # 1-indexed
climatologies = np.full((n_lat, n_lon, 367), np.nan, dtype=np.float64)

# To avoid nested loops over lat/lon, we can group by doy
for d in range(1, 367):
    if d == 60:
        continue
    
    # Pool: every SST value whose date lies within +/- 5 calendar days 
    # of a baseline date (1992-01-01 to 2002-12-31) whose day of year is d.
    
    # First, find baseline dates (1992-01-01 to 2002-12-31) that have doy == d
    baseline_mask = (baseline_times >= pd.Timestamp(baseline_start)) & \
                    (baseline_times <= pd.Timestamp(baseline_end)) & \
                    (baseline_doys == d)
    
    target_baseline_dates = baseline_times[baseline_mask]
    
    # Now, for each such date, we need the window [date-5, date+5]
    # This can be a lot of overlapping windows.
    # Better: for each day in baseline_ext, is it within 5 days of any target_baseline_date?
    # Actually, the rule is: a date is in the pool if it's within 5 days of ANY 
    # baseline date (1992-2002) with doy d.
    
    # Let's find all dates in baseline_ext that are in the pool for doy d.
    pool_indices = []
    for date in target_baseline_dates:
        start_win = date - timedelta(days=5)
        end_win = date + timedelta(days=5)
        # Find indices of baseline_times in this range
        # Since baseline_times is sorted, we can use searchsorted
        idx_start = np.searchsorted(baseline_times, start_win)
        idx_end = np.searchsorted(baseline_times, end_win, side='right')
        pool_indices.extend(range(idx_start, idx_end))
    
    pool_indices = sorted(list(set(pool_indices)))
    
    if pool_indices:
        # Extract SST for these indices: (time, lat, lon)
        pool_data = sst_baseline.values[pool_indices, :, :]
        
        # Compute 90th percentile (hazen) and mean across the time axis
        # numpy.nanquantile(..., method='hazen')
        thresholds[:, :, d] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
        climatologies[:, :, d] = np.nanmean(pool_data, axis=0)

# Handle day 60
thresholds[:, :, 60] = (thresholds[:, :, 59] + thresholds[:, :, 61]) / 2
climatologies[:, :, 60] = (climatologies[:, :, 59] + climatologies[:, :, 61]) / 2

# Smoothing: 31-day centred moving mean, wrap around (modulo 366)
def smooth_array(arr):
    # arr shape: (lat, lon, 367) - we use 1-366
    # Create a 366-element array (0-365)
    smoothed = np.full((n_lat, n_lon, 367), np.nan, dtype=np.float64)
    
    # Work with a 0-indexed 366 array
    data = arr[:, :, 1:] # (lat, lon, 366)
    res = np.full_like(data, np.nan)
    
    for d in range(366):
        # Days d-15 to d+15 modulo 366
        window = [ (d + i) % 366 for i in range(-15, 16) ]
        res[:, :, d] = np.nanmean(data[:, :, window], axis=2)
        
    smoothed[:, :, 1:] = res
    return smoothed

thresholds_smoothed = smooth_array(thresholds)
climatologies_smoothed = smooth_array(climatologies)

# Now detect MHWs in target period
# target_ds: time from 2014-06-01 to 2014-08-31
target_times = pd.to_datetime(target_ds.time.values)
target_doys = np.array([get_doy_custom(t) for t in target_times])

# SST: (time, lat, lon)
sst_vals = sst_target.values # float64
# Thresholds for target days: (time, lat, lon)
# we need thresholds_smoothed[:, :, target_doys]
target_thresholds = thresholds_smoothed[:, :, target_doys] # (lat, lon, time)
# Transpose to (time, lat, lon)
target_thresholds = np.transpose(target_thresholds, (2, 0, 1))

# hot = SST >= threshold
hot = sst_vals >= target_thresholds

# Per-cell MHWs
# hot shape: (time, lat, lon)
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not is_sea[i, j]:
            continue
            
        cell_hot = hot[:, i, j]
        # Find runs of hot days
        # A run of at least 5 consecutive hot days
        # Join gaps of 1 or 2 non-hot days
        
        # Convert boolean to int for processing
        hot_int = cell_hot.astype(int)
        
        # Use a simple algorithm to find MHWs
        # First, find all runs of hot days
        # Then merge them if gap <= 2
        
        # find boundaries of hot segments
        diff = np.diff(np.concatenate(([0], hot_int, [0])))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0] # end is exclusive
        
        runs = []
        for s, e in zip(starts, ends):
            if e - s >= 5:
                runs.append([s, e])
        
        # Merge runs with gap <= 2
        merged_runs = []
        if runs:
            curr_s, curr_e = runs[0]
            for next_s, next_e in runs[1:]:
                if next_s - curr_e <= 3: # gap = next_s - curr_e - 1. gap <= 2 means next_s - curr_e <= 3
                    # wait, gap is non-hot days. 
                    # if curr_e is the first non-hot day, and next_s is the next hot day:
                    # gap is next_s - curr_e.
                    # example: curr_e=10 (index 10 is 0), next_s=11 (index 11 is 1). gap=1.
                    # if curr_e=10, next_s=12. gap=2.
                    # if curr_e=10, next_s=13. gap=3.
                    # So we merge if next_s - curr_e <= 3? 
                    # Let's re-evaluate.
                    # hot: [1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1]
                    # starts: [0], ends: [5] (run 0-5), starts: [7], ends: [12] (run 7-12)
                    # curr_e = 5, next_s = 7. gap = 7 - 5 = 2. This should be merged.
                    # gap is simply next_s - curr_e. Wait, no.
                    # curr_e is the index of the first non-hot day after the run.
                    # next_s is the index of the first hot day of the next run.
                    # The number of non-hot days between them is next_s - curr_e.
                    # Example: curr_e=5, next_s=6. gap=1. (index 5 is non-hot)
                    # Example: curr_e=5, next_s=7. gap=2. (indices 5, 6 are non-hot)
                    # So merge if next_s - curr_e <= 2.
                    # Wait, I used a different logic. Let's be precise.
                    pass
                pass
        
        # Let's rewrite the merge logic carefully.
        # (Implemented below in the final block)

# To save time and avoid errors, I'll put the logic in a cleaner function.
