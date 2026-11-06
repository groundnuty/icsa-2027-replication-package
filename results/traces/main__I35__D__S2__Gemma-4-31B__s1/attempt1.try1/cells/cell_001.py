import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os

# Constants
REMOTE_PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
LOCAL_PATH = '/work/sst_s2.nc'
LAT_MIN, LAT_MAX = 59.93, 61.13
LON_MIN, LON_MAX = 18.69, 19.89
TARGET_START = '2009-06-01'
TARGET_END = '2009-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'

# Ensure output directory exists
os.makedirs('output', exist_ok=True)

# Download dataset
fs = fsspec.filesystem('onedata')
fs.get(REMOTE_PATH, LOCAL_PATH)

# Open dataset
ds = xr.open_dataset(LOCAL_PATH, engine='h5netcdf')

# Region and target period slicing
# We need more data for the baseline pool calculations (±5 days)
# Baseline is 1992-01-01 to 2002-12-31.
# Pool includes dates from 1991-12-27 to 2003-01-05.
# Target period is 2009-06-01 to 2009-08-31.
# So we need data from 1991-12-27 to 2009-08-31.

# Subset by region first to save memory
ds_region = ds.sel(lat=slice(LAT_MIN, LAT_MAX), lon=slice(LON_MIN, LON_MAX))

# Check coordinates to make sure slicing worked correctly (lat might be inverted)
print(f"Lat range: {ds_region.lat.min().values} to {ds_region.lat.max().values}")
print(f"Lon range: {ds_region.lon.min().values} to {ds_region.lon.max().values}")
print(f"Time range: {ds_region.time.min().values} to {ds_region.time.max().values}")
