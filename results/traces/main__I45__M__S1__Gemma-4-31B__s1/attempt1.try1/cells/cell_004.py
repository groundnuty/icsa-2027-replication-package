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

def get_doy(dt):
    # 1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61 ...
    # pd.Timestamp.dayofyear does this (1-indexed)
    return dt.dayofyear

# 1. Region and Target Period data
# We need SST for the region for:
# - target period (2009-06-01 to 2009-08-31)
# - baseline period + windows (1991-12-27 to 2003-01-05)

# Since the dataset is a collection of files, we'll need to filter them.
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

# Identify sea cells
# First, load target period data for the region
target_files = get_files_for_range(TARGET_START, TARGET_END)
target_dates = [pd.to_datetime(f[4:12], format='%Y%m%d') for f in target_files]

# We'll load the region's SST. 
# To avoid loading too much into memory, we'll slice by lat/lon.

def load_region_sst(files):
    datasets = []
    for f in files:
        ds = xr.open_dataset(os.path.join(DIR_PATH, f), engine='h5netcdf')
        # Slice region
        ds_region = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
        datasets.append(ds_region)
    return xr.concat(datasets, dim='time')

# Load target data to find sea cells
ds_target = load_region_sst(target_files)
# SST is 'analysed_sst'
sst_target = ds_target['analysed_sst'].astype('float64')

# Sea cells: SST is finite on every day of target period
# sst_target shape: (time, lat, lon)
# We want a mask of shape (lat, lon)
is_finite = np.all(np.isfinite(sst_target.values), axis=0)
sea_cells_mask = is_finite

print(f"Region shape: {sst_target.shape}")
print(f"Number of sea cells: {np.sum(sea_cells_mask)}")
print(f"Target days: {len(target_dates)}")
