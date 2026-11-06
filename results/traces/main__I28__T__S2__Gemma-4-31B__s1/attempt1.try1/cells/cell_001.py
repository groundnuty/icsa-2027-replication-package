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
target_start = "2013-06-01"
target_end = "2013-08-31"
baseline_start = "1992-01-01"
baseline_end = "2002-12-31"

# Subset region
ds_reg = ds.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

# Print region info to verify
print(f"Region lat: {ds_reg.lat.values}, lon: {ds_reg.lon.values}")
print(f"Time range: {ds_reg.time.values[0]} to {ds_reg.time.values[-1]}")
