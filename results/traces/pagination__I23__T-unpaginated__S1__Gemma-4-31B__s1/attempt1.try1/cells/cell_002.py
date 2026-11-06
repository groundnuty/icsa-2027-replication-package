import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

# Spatial bounds
lat_min, lat_max = 57.41, 58.61
lon_min, lon_max = 18.69, 19.89

# Time periods
baseline_start = pd.to_datetime('1992-01-01')
baseline_end = pd.to_datetime('2002-12-31')
# Window extension for pools
pool_start = baseline_start - pd.Timedelta(days=5)
pool_end = baseline_end + pd.Timedelta(days=5)
target_start = pd.to_datetime('2013-06-01')
target_end = pd.to_datetime('2013-08-31')

# Get all relevant files
all_files = fs.ls(base_path)
relevant_files = []
for f in all_files:
    # Filename format: sst_YYYYMMDD.nc
    date_str = f.split('_')[-1].replace('.nc', '')
    f_date = pd.to_datetime(date_str)
    if (pool_start <= f_date <= pool_end) or (target_start <= f_date <= target_end):
        relevant_files.append(f)
relevant_files.sort()

# Load a sample file to check coordinates
with fs.open(relevant_files[0], "rb") as f:
    ds_sample = xr.open_dataset(f, engine="h5netcdf")
    print(ds_sample.coords)
    print(ds_sample.data_vars)
    print(f"Lat range: {ds_sample.lat.min().values}, {ds_sample.lat.max().values}")
    print(f"Lon range: {ds_sample.lon.min().values}, {ds_sample.lon.max().values}")
