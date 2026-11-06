
import numpy as np
import datetime as dt
import xarray as xr
import json
import os

print("Loading data...")
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min_idx, lat_max_idx = 34, 93
lon_min_idx, lon_max_idx = 213, 272

times = ds.time.values
lats = ds.latitude.values[lat_min_idx:lat_max_idx+1]
lons = ds.longitude.values[lon_min_idx:lon_max_idx+1]

# Define date ranges
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')

# Find indices
baseline_mask = (times >= baseline_start) & (times <= baseline_end)
target_mask = (times >= target_start) & (times <= target_end)

baseline_idx = np.where(baseline_mask)[0]
target_idx = np.where(target_mask)[0]

print(f"Baseline idx: {len(baseline_idx)}, Target idx: {len(target_idx)}")

# Load data directly with isel - just the region subset
baseline_sst = ds['analysed_sst'].isel(time=baseline_idx, latitude=slice(lat_min_idx, lat_max_idx+1), longitude=slice(lon_min_idx, lon_max_idx+1)).values.astype(np.float64)
print(f"Baseline loaded: {baseline_sst.shape}")

# Free memory
del ds['analysed_sst']
