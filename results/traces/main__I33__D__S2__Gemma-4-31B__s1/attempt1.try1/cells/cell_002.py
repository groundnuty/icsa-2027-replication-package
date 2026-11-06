import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# Open dataset and slice for region
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")

lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45

# Crop region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Time slices
baseline_start = '1991-12-27'
baseline_end = '2003-01-05'
target_start = '2014-06-01'
target_end = '2014-08-31'

# Extract slices
ds_baseline = ds_region.sel(time=slice(baseline_start, baseline_end)).load()
ds_target = ds_region.sel(time=slice(target_start, target_end)).load()

print(f"Baseline shape: {ds_baseline.analysed_sst.shape}")
print(f"Target shape: {ds_target.analysed_sst.shape}")
print(f"Lats: {ds_region.latitude.values}")
print(f"Lons: {ds_region.longitude.values}")
