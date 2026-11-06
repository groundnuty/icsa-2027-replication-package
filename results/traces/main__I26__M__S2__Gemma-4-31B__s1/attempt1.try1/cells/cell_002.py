import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

# Dataset path
ds_path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Region and time bounds
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61
target_start_str = '2007-06-01'
target_end_str = '2007-08-31'
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'
baseline_load_start_str = '1991-12-27'
baseline_load_end_str = '2003-01-05'

# Open dataset
ds = xr.open_dataset(ds_path, engine="h5netcdf")

# Subset region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Time indices for baseline load and target period
time_all = ds_region.time.values
target_mask = (time_all >= np.datetime64(target_start_str)) & (time_all <= np.datetime64(target_end_str))
baseline_load_mask = (time_all >= np.datetime64(baseline_load_start_str)) & (time_all <= np.datetime64(baseline_load_end_str))

# Extract the SST data for these periods
sst_target = ds_region.analysed_sst.sel(time=slice(target_start_str, target_end_str)).values.astype(np.float64)
sst_baseline_load = ds_region.analysed_sst.sel(time=slice(baseline_load_start_str, baseline_load_end_str)).values.astype(np.float64)

# Get the time coordinates for these slices
time_target = ds_region.time.sel(time=slice(target_start_str, target_end_str)).values
time_baseline_load = ds_region.time.sel(time=slice(baseline_load_start_str, baseline_load_end_str)).values

print(f"Target shape: {sst_target.shape}") # (time, lat, lon)
print(f"Baseline load shape: {sst_baseline_load.shape}")
print(f"Target time range: {time_target[0]} to {time_target[-1]}")
print(f"Baseline load time range: {time_baseline_load[0]} to {time_baseline_load[-1]}")
