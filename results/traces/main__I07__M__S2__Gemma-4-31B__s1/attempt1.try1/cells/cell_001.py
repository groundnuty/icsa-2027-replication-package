import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

# Path to dataset
ds_path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Region and Period
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
target_start = '2021-06-01'
target_end = '2021-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

# Open dataset
ds = xr.open_dataset(ds_path, engine="h5netcdf")

# Subset region
ds_region = ds.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

# Define time ranges
t_start = pd.to_datetime(target_start)
t_end = pd.to_datetime(target_end)
b_start = pd.to_datetime(baseline_start)
b_end = pd.to_datetime(baseline_end)

# For baseline pools, we need [b_start - 5, b_end + 5]
b_pool_start = b_start - pd.Timedelta(days=5)
b_pool_end = b_end + pd.Timedelta(days=5)

# Slice target and baseline data
# Use a union of target and baseline pool ranges to avoid multiple loads if possible
# But the target is far from the baseline, so we just slice what we need.
ds_target = ds_region.sel(time=slice(t_start, t_end))
ds_baseline = ds_region.sel(time=slice(b_pool_start, b_pool_end))

print(f"Target time range: {ds_target.time.values[0]} to {ds_target.time.values[-1]}")
print(f"Baseline pool range: {ds_baseline.time.values[0]} to {ds_baseline.time.values[-1]}")
print(f"Region shape: {ds_region.lat.size}x{ds_region.lon.size}")
