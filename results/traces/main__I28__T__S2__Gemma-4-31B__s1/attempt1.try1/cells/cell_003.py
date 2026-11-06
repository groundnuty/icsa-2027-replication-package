import xarray as xr
import numpy as np
import pandas as pd
import json
import fsspec
from datetime import datetime, timedelta

# Setup filesystem and open dataset
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")

# Region and time bounds
lat_min, lat_max = 57.85, 59.05
lon_min, lon_max = 21.01, 22.21
target_start_str = "2013-06-01"
target_end_str = "2013-08-31"
baseline_start_str = "1992-01-01"
baseline_end_str = "2002-12-31"

# Subset region
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Target period subset for sea cell identification
target_start = pd.Timestamp(target_start_str)
target_end = pd.Timestamp(target_end_str)
ds_target = ds_reg.sel(time=slice(target_start, target_end))

# 1. Sea cells: SST is finite on every day of the target period
sst_target = ds_target['analysed_sst']
# Check for NaN or Inf
is_finite = np.isfinite(sst_target)
sea_cells_mask = is_finite.all(dim='time')

# 2. Threshold and climatology
# Baseline period dates
baseline_start = pd.Timestamp(baseline_start_str)
baseline_end = pd.Timestamp(baseline_end_str)

# Get all dates in the dataset that could possibly be in a pool
# Window range is baseline_start - 5 to baseline_end + 5
pool_range_start = baseline_start - pd.Timedelta(days=5)
pool_range_end = baseline_end + pd.Timedelta(days=5)
ds_pool_data = ds_reg.sel(time=slice(pool_range_start, pool_range_end))

# Pre-calculate day of year for all dates in the baseline and pool range
times = pd.to_datetime(ds_pool_data.time.values)
doy = np.array([t.dayofyear for t in times])

# To efficiently find pools, we can create a mapping from doy to indices
doy_to_indices = {}
for i, d in enumerate(doy):
    if d not in doy_to_indices:
        doy_to_indices[d] = []
    doy_to_indices[d].append(i)

#- To correctly handle the "baseline date (1992-01-01 to 2002-12-31)"
baseline_mask = (times >= baseline_start) & (times <= baseline_end)

# The pools for d in {1..366}, d != 60
thresholds = np.full(366, np.nan, dtype=np.float64)
climatology = np.full(366, np.nan, dtype=np.float64)

# We need these per cell. Let's use arrays: (366, nlat, nlon)
nlat = len(ds_reg.latitude)
nlon = len(ds_reg.longitude)
thresholds_all = np.full((366, nlat, nlon), np.nan, dtype=np.float64)
climatology_all = np.full((366, nlat, nlon), np.nan, dtype=np.float64)

# SST values for the pool range
sst_values = ds_pool_data['analysed_sst'].values.astype(np.float64)

# To optimize, let's only compute for sea cells
sea_indices_lat = []
sea_indices_lon = []
sea_cell_coords = []
for i in range(nlat):
    for j in range(nlon):
        if sea_cells_mask.values[i, j]:
            sea_indices_lat.append(i)
            sea_indices_lon.append(j)
            sea_cell_coords.append((i, j))

# Pre-calculate the set of dates for each doy pool
# "For each day of year d other than 60, the pool is every SST value whose date lies within ±5 calendar days of a baseline date ... whose day of year is d."
doy_pools = {}
all_times = times
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find baseline dates with day of year d
    baseline_dates_with_doy_d = all_times[(all_times >= baseline_start) & 
                                         (all_times <= baseline_end) & 
                                         (np.array([t.dayofyear for t in all_times]) == d)]
    
    pool_indices = set()
    for b_date in baseline_dates_with_doy_d:
        # Window [b_date - 5, b_date + 5]
        # Find indices of times within this window
        # Since all_times is sorted, we can use searchsorted
        start_idx = np.searchsorted(all_times, b_date - pd.Timedelta(days=5))
        end_idx = np.searchsorted(all_times, b_date + pd.Timedelta(days=5), side='right')
        pool_indices.update(range(start_idx, end_idx))
    
    doy_pools[d] = list(pool_indices)

# Now compute for each sea cell
for i, j in sea_cell_coords:
    cell_sst = sst_values[:, i, j]
    for d, indices in doy_pools.items():
        pool = cell_sst[indices]
        # Ignore NaNs
        pool = pool[~np.isnan(pool)]
        if len(pool) > 0:
            thresholds_all[d-1, i, j] = np.quantile(pool, 0.9, method='hazen')
            climatology_all[d-1, i, j] = np.nanmean(pool)

# 2. Set day 60 to the mean of days 59 and 61
thresholds_all[59] = (thresholds_all[58] + thresholds_all[60]) / 2
climatology_all[59] = (climatology_all[58] + climatology_all[60]) / 2

# 2. Smoothing: 31-day centred moving mean (wrap around)
def smooth_31(arr):
    # arr is (366, nlat, nlon)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # Window is [d-15, d+15] modulo 366
        # indices: (d-15) % 366, ..., (d+15) % 366
        indices = [(d + k) % 366 for k in range(-15, 16)]
        # Mean across the time dimension for all cells
        # Use nanmean to be safe, although we expect values for sea cells
        smoothed[d] = np.nanmean(arr[indices], axis=0)
    return smoothed

thresholds_smoothed = smooth_31(thresholds_all)
climatology_smoothed = smooth_31(climatology_all)

# 3. Per-cell MHWs
# Target period: 2013-06-01 to 2013-08-31
target_times = pd.to_datetime(ds_target.time.values)
target_doy = np.array([t.dayofyear for t in target_times])
target_sst = sst_target.values.astype(np.float64)

# Hot days: SST >= threshold
# thresholds_smoothed is (366, nlat, nlon)
# target_sst is (ntime, nlat, nlon)
# target_doy is (ntime,)
# We need to index thresholds_smoothed by target_doy
# Note: target_doy are 1-indexed.
hot_days = np.zeros(target_sst.shape, dtype=bool)
for t in range(len(target_times)):
    d = target_doy[t]
    # day 60 exists in target_doy if 2013 was a leap year (it wasn't)
    # But let's be general. d is 1-indexed.
    #- Wait, the smoothing was done on a 366-element array.
    # If 2013 is not a leap year, doy 60 doesn't exist.
    # The thresholds_smoothed array has 366 elements.
    # If d=60, we use index 59.
    # Let's check: if a year is not leap, day 60 in our index is Mar 1?
    # No, the mapping is 1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61.
    # So if the year is not leap, 1 Mar is day 60 in terms of calendar day of year?
    # Let's check: pd.Timestamp("2013-03-01").dayofyear is 60.
    # "Non-leap years have no day 60."
    # This means we must map the dates to our 1-366 scale.
    # My `target_doy` uses `t.dayofyear`. For 2013-03-01, it's 60.
    # But the method says: "Non-leap years have no day 60."
    # This implies that for non-leap years, we should shift days after Feb 28.
    # Let's create a custom doy function.
    pass

# Re-do the day-of-year mapping as specified
def get_custom_doy(dt):
    # dt is pd.Timestamp
    # 1 Jan = 1
    # 28 Feb = 59
    # 29 Feb = 60
    # 1 Mar = 61
    if dt.month < 3:
        return dt.timetuple().tm_yday
    else:
        if dt.is_leap_year:
            return dt.timetuple().tm_yday
        else:
            return dt.timetuple().tm_yday + 1

# Re-calculate target_doy
target_doy_custom = np.array([get_custom_doy(t) for t in target_times])

# Also need to re-calculate the pool indices and thresholds using this custom doy
# Let's rewrite the whole logic in one go to be consistent.
