
import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region bounds
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_indices = np.where((lat_vals >= lat_min) & (lat_vals <= lat_max))[0]
lon_indices = np.where((lon_vals >= lon_min) & (lon_vals <= lon_max))[0]

time_vals = ds.time.values

# Baseline: 1991-12-27 to 2003-01-05
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time_vals >= baseline_start) & (time_vals <= baseline_end)
baseline_time_indices = np.where(baseline_mask)[0]
print(f"Baseline time indices: {baseline_time_indices[0]} to {baseline_time_indices[-1]}, count={len(baseline_time_indices)}")

# Target: 2015-06-01 to 2015-08-31
target_start = np.datetime64('2015-06-01')
target_end = np.datetime64('2015-08-31')
target_mask = (time_vals >= target_start) & (time_vals <= target_end)
target_time_indices = np.where(target_mask)[0]
print(f"Target time indices: {target_time_indices[0]} to {target_time_indices[-1]}, count={len(target_time_indices)}")
