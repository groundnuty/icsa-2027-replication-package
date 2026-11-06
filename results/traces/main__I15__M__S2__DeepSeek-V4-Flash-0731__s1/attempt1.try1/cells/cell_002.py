
import xarray as xr
import numpy as np

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# Region bounds
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

# Find lat/lon indices
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= lat_min) & (lat_sel <= lat_max))[0]
lon_idx = np.where((lon_sel >= lon_min) & (lon_sel <= lon_max))[0]
print("lat_idx", lat_idx.min(), lat_idx.max(), "count", len(lat_idx))
print("lon_idx", lon_idx.min(), lon_idx.max(), "count", len(lon_idx))
print("lat values", lat_sel[lat_idx.min()], lat_sel[lat_idx.max()])
print("lon values", lon_sel[lon_idx.min()], lon_sel[lon_idx.max()])

# Check time range
print("time range", ds.time.values[0], ds.time.values[-1])

# Target period
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
time_vals = ds.time.values
target_idx = np.where((time_vals >= target_start) & (time_vals <= target_end))[0]
print("target idx", target_idx.min(), target_idx.max(), "count", len(target_idx))
