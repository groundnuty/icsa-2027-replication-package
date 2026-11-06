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
target_start_date = pd.Timestamp("2013-06-01")
target_end_date = pd.Timestamp("2013-08-31")
baseline_start_date = pd.Timestamp("1992-01-01")
baseline_end_date = pd.Timestamp("2002-12-31")

# Correct dimension names
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

print(f"Region latitude: {ds_reg.latitude.values}, longitude: {ds_reg.longitude.values}")
print(f"Time range: {ds_reg.time.values[0]} to {ds_reg.time.values[-1]}")
print(f"Variables: {list(ds_reg.data_vars)}")
