import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Parameters
LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
TARGET_START = "2003-06-01"
TARGET_END = "2003-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"

# Data path
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

fs = fsspec.filesystem('onedata')
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

# Open dataset and slice region
ds = xr.open_dataset(local_path, engine="h5netcdf")
ds_region = ds.sel(
    latitude=slice(LAT_MIN, LAT_MAX),
    longitude=slice(LON_MIN, LON_MAX)
).compute() # Load into memory since it's a small region

sst = ds_region['analysed_sst']
# Convert to float64 for precision
sst = sst.astype(np.float64)

# Define time ranges
time_baseline_start = np.datetime64(BASELINE_START)
time_baseline_end = np.datetime64(BASELINE_END)
time_target_start = np.datetime64(TARGET_START)
time_target_end = np.datetime64(TARGET_END)

# Target period mask
target_mask = (sst.time >= time_target_start) & (sst.time <= time_target_end)
sst_target = sst.sel(time=target_mask)

# 1. Sea cells: SST is finite on every day of the target period
# Sea cells are those where no NaN values are present in the target period
# sst_target is (time, lat, lon). We want cells (lat, lon) where all time values are finite.
is_sea = np.all(np.isfinite(sst_target.values), axis=0)

# 2. Threshold and climatology
# Need data from BASELINE_START - 5 to BASELINE_END + 5
pool_start = time_baseline_start - np.timedelta64(5, 'D')
pool_end = time_baseline_end + np.timedelta64(5, 'D')
sst_pool = sst.sel(time=slice(pool_start, pool_end))

def get_day_of_year(dt):
    # 1 Jan = 1, ... 29 Feb = 60, ... 31 Dec = 366
    # pandas.Timedelta/datetime are easier
    return dt.dayofyear

# Create a mapping from date to day-of-year
baseline_dates = pd.date_range(BASELINE_START, BASELINE_END)
# Baseline date's day of year (1-366)
# Note: pd.Series.dt.dayofyear handles leap years correctly.

# We need to iterate through d = 1 to 366 (excluding 60)
thresholds = np.full((366, sst.latitude.size, sst.longitude.size), np.nan)
climatology = np.full((366, sst.latitude.size, sst.longitude.size), np.nan)

# Convert sst_pool to a numpy array for faster access
# sst_pool coordinates
pool_times = pd.to_datetime(sst_pool.time.values)
pool_vals = sst_pool.values # (time, lat, lon)

# For each day of year d (1-366), d != 60:
# Pool = SST values whose date is within ±5 days of any baseline date with day of year d.
# A baseline date B has day of year d. The window is [B-5, B+5].
# This is equivalent to: for each date T in the pool, it contributes to the pool of day d
# if there exists a baseline date B such that B.dayofyear == d and |T - B| <= 5 days.

# Let's pre-calculate the day-of-year for each date in the pool
pool_days_of_year = pool_times.dayofyear.values
pool_dates_np = pool_times.values

# Let's pre-calculate which baseline dates have which day of year
baseline_days_of_year = baseline_dates.dayofyear.values
baseline_dates_np = baseline_dates.values

# Optimization: for each day of year d, find all baseline dates with that day of year,
# then find all dates in the pool that are within 5 days of any of those baseline dates.
for d in range(1, 367):
    if d == 60:
        continue
    
    # Baseline dates with day of year d
    b_indices = np.where(baseline_days_of_year == d)[0]
    if len(b_indices) == 0:
        continue
    
    # All baseline dates with day of year d
    b_dates = baseline_dates_np[b_indices]
    
    # Find all dates T in pool such that there is some B in b_dates with |T - B| <= 5 days
    # Using broadcasting or a loop
    mask_pool = np.zeros(len(pool_dates_np), dtype=bool)
    for b_date in b_dates:
        diff = np.abs(pool_dates_np - b_date)
        mask_pool |= (diff <= np.timedelta64(5, 'D'))
    
    pool_data = pool_vals[mask_pool, :, :]
    
    # Threshold: 90th percentile (method="hazen"), ignoring NaN
    # np.nanquantile doesn't have "hazen". 
    # Hazen is (i - 0.5) / n. 
    # Let's use a helper for Hazen quantile.
    
    # For each cell (lat, lon):
    # data = pool_data[:, lat, lon]
    # filtered = data[~np.isnan(data)]
    # if len(filtered) > 0:
    #     thresholds[d-1, lat, lon] = hazen_quantile(filtered, 0.9)
    #     climatology[d-1, lat, lon] = np.mean(filtered)
    
    # Vectorized quantile calculation is tricky with NaNs.
    # We can use np.nanpercentile with linear interpolation, but the requirement is "hazen".
    # Hazen (Type 5): q(p) = (n+1)p - 0.5 index.
    # Actually, let's implement a function.
    
    # To speed up, we process the whole pool_data array.
    # But the number of non-NaNs varies per cell.
    
    # We can use np.nanmean for climatology
    climatology[d-1, :, :] = np.nanmean(pool_data, axis=0)
    
    # For threshold, we can't easily vectorize hazen quantile with NaNs.
    # Let's do it cell by cell or in chunks.
    # Given the region size is small (lat: 60.09-61.29, lon: 20.01-21.21)
    # Let's see the size of sst_region.
    
# Let's refine the quantile function and the loop.
