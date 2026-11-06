import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

# Setup
fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Open dataset
with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")

# Define region and periods
lat_min, lat_max = 55.67, 56.87
lon_min, lon_max = 16.45, 17.65
target_start = '2005-06-01'
target_end = '2005-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

# Subset region
ds_region = ds.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

# Target period SST
sst_target = ds_region.sel(time=slice(target_start, target_end))

# Identify sea cells: SST finite on every day of target period
# Use .all(dim='time') on a boolean mask of finite values
finite_mask = np.isfinite(sst_target.sst).all(dim='time')
sea_cells = finite_mask

# Baseline range + window buffers
baseline_dt_start = pd.to_datetime(baseline_start)
baseline_dt_end = pd.to_datetime(baseline_end)
window_start = baseline_dt_start - timedelta(days=5)
window_end = baseline_dt_end + timedelta(days=5)

# Subset dataset for baseline + buffers
ds_baseline_full = ds_region.sel(time=slice(window_start.strftime('%Y-%m-%d'), window_end.strftime('%Y-%m-%d')))
sst_baseline = ds_baseline_full.sst

# Coordinate info for the target period
target_times = sst_target.time.values
target_lat = sst_target.lat.values
target_lon = sst_target.lon.values

print(f"Region shape: {ds_region.sst.shape}")
print(f"Sea cells count: {int(sea_cells.sum())}")
print(f"Target period days: {len(target_times)}")
