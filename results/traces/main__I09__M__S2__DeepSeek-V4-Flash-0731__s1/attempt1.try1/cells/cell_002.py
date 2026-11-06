
import xarray as xr
import numpy as np

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# Region bounds
lat_min, lat_max = 54.81, 56.01
lon_min, lon_max = 19.61, 20.81

# Find grid cells in region
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_mask = (lat_sel >= lat_min) & (lat_sel <= lat_max)
lon_mask = (lon_sel >= lon_min) & (lon_sel <= lon_max)
print("lat indices:", np.where(lat_mask)[0])
print("lon indices:", np.where(lon_mask)[0])
print("lat values:", lat_sel[lat_mask])
print("lon values:", lon_sel[lon_mask])

# Target period
import pandas as pd
target_start = np.datetime64('2022-06-01')
target_end = np.datetime64('2022-08-31')
time_vals = ds.time.values
print("time range:", time_vals[0], time_vals[-1])
