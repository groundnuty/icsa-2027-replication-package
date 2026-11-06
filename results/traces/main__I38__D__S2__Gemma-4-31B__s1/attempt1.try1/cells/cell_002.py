import xarray as xr
import numpy as np
import pandas as pd
import json
import fsspec
from datetime import datetime, timedelta

# Re-open dataset
local_path = '/work/sst_s2.nc'
ds = xr.open_dataset(local_path, engine="h5netcdf")

# Region and Period
lat_min, lat_max = 60.49, 61.69
lon_min, lon_max = 17.25, 18.45
target_start = '2003-06-01'
target_end = '2003-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

# Time range for baseline windows
# The pool for DOY 1 on 1992-01-01 starts 5 days earlier.
window_start = '1991-12-27'
window_end = '2003-08-31'

# Slice the region and time
ds_region = ds.sel(
    latitude=slice(lat_min, lat_max),
    longitude=slice(lon_min, lon_max),
    time=slice(window_start, window_end)
)

# Convert to float64 for precision
sst = ds_region['analysed_sst'].astype(np.float64)

print(f"SST shape: {sst.shape}")
print(f"Time range: {sst.time.values[0]} to {sst.time.values[-1]}")
print(f"Lat range: {sst.latitude.values[0]} to {sst.latitude.values[-1]}")
print(f"Lon range: {sst.longitude.values[0]} to {sst.longitude.values[-1]}")
