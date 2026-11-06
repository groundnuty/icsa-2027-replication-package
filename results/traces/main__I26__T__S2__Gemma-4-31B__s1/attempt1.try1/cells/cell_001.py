import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os

# Configuration
region = {"lat_min": 57.83, "lat_max": 59.03, "lon_min": 17.41, "lon_max": 18.61}
target_start = "2007-06-01"
target_end = "2007-08-31"
baseline_start = "1992-01-01"
baseline_end = "2002-12-31"
file_path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"

def get_doy(date):
    month = date.month
    day = date.day
    month_lengths = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_lengths[:month-1]) + day

def get_baseline_dates_for_doy(d, baseline_dates):
    # d is the DOY (1-366)
    # baseline_dates is a pd.DatetimeIndex from 1992-01-01 to 2002-12-31
    # Find all dates in baseline_dates with DOY == d
    # Then for each, add +/- 5 days window.
    
    # Filter baseline dates with DOY d
    # Note: get_doy is slow for large arrays, so maybe precalculate
    matching_dates = [t for t in baseline_dates if get_doy(t) == d]
    
    pool_dates = set()
    for t_base in matching_dates:
        window = pd.date_range(t_base - pd.Timedelta(days=5), t_base + pd.Timedelta(days=5))
        pool_dates.update(window)
    
    return sorted(list(pool_dates))

# Start processing
fs = fsspec.filesystem('onedata')
with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")

print("Dataset coordinates:", ds.coords)
print("Dataset variables:", ds.data_vars)

# Slice region
ds_region = ds.sel(
    lat=slice(region["lat_min"], region["lat_max"]),
    lon=slice(region["lon_min"], region["lon_max"])
)

# We need SST for the baseline and target periods.
# The baseline windows can extend slightly outside 1992-2002.
# Baseline: 1992-01-01 to 2002-12-31. 
# Windows: +/- 5 days.
# Min date: 1992-01-01 - 5 days = 1991-12-27
# Max date: 2002-12-31 + 5 days = 2003-01-05
# Target: 2007-06-01 to 2007-08-31

# To be safe, load all necessary time slices
all_times = np.concatenate([
    pd.date_range("1991-12-27", "2003-01-05"),
    pd.date_range(target_start, target_end)
])

# Convert all_times to the dataset's time format (likely datetime64)
# The dataset likely has a 'time' coordinate.
# Let's check if we can just use slice/sel.

# Slice by time
# We'll do this in two parts to avoid loading too much if needed, 
# but these are small enough.
ds_baseline_ext = ds_region.sel(time=slice("1991-12-27", "2003-01-05"))
ds_target = ds_region.sel(time=slice(target_start, target_end))

# Keep only SST (the variable is likely 'thetao' or 'sst')
# Checking the variable name from the dataset tools if possible, but I'll use the printed data_vars.
# Based on typical CMEMS SST, it's likely 'sst'.
var_name = 'sst' if 'sst' in ds.data_vars else 'thetao'
sst_baseline_ext = ds_baseline_ext[var_name].astype(np.float64)
sst_target = ds_target[var_name].astype(np.float64)

print("SST baseline shape:", sst_baseline_ext.shape)
print("SST target shape:", sst_target.shape)
