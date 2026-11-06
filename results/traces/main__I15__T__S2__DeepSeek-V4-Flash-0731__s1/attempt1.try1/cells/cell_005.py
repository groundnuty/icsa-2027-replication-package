
import fsspec
import xarray as xr
import numpy as np
import pandas as pd
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Find region indices
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

lat_sel = ds.latitude[(ds.latitude >= lat_min) & (ds.latitude <= lat_max)]
lon_sel = ds.longitude[(ds.longitude >= lon_min) & (ds.longitude <= lon_max)]
lat_idx = ds.latitude.values >= lat_min
lat_idx &= ds.latitude.values <= lat_max
lon_idx = ds.longitude.values >= lon_min
lon_idx &= ds.longitude.values <= lon_max

# Find time indices
time_vals = ds.time.values
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
time_idx_target = (time_vals >= target_start) & (time_vals <= target_end)
print('Target time count:', time_idx_target.sum())
print('Time values:', time_vals[time_idx_target][0], time_vals[time_idx_target][-1])

# Baseline: need days from 1991-12-27 to 2003-01-05 (for window)
base_start_ext = np.datetime64('1991-12-27')
base_end_ext = np.datetime64('2003-01-05')
time_idx_base = (time_vals >= base_start_ext) & (time_vals <= base_end_ext)
print('Extended baseline count:', time_idx_base.sum())

print('Lat indices:', np.where(lat_idx)[0][0], np.where(lat_idx)[0][-1], 'count:', lat_idx.sum())
print('Lon indices:', np.where(lon_idx)[0][0], np.where(lon_idx)[0][-1], 'count:', lon_idx.sum())
