import xarray as xr
import numpy as np
import pandas as pd
import json
import fsspec
from datetime import datetime, timedelta

# Initialize filesystem
fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open dataset
ds = xr.open_dataset(local_path, engine="h5netcdf")

# Define region and periods
lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45
target_start = '2014-06-01'
target_end = '2014-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'
# Expanded baseline for windows
expanded_start = '1991-12-27'
expanded_end = '2003-01-05'

# Slice region
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Variable name
sst_var = 'thetao' # Looking at common CMEMS SST names, but I should check.
# Let's check variable names.
print(ds_reg.data_vars)
