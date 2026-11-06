
import xarray as xr
import numpy as np
import os

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# Let's inspect the coordinate names and values
print("lat range:", ds.latitude.values.min(), ds.latitude.values.max())
print("lon range:", ds.longitude.values.min(), ds.longitude.values.max())
print("time range:", ds.time.values.min(), ds.time.values.max())

# Region
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

# Find indices
lat_idx = np.where((ds.latitude.values >= lat_min) & (ds.latitude.values <= lat_max))[0]
lon_idx = np.where((ds.longitude.values >= lon_min) & (ds.longitude.values <= lon_max))[0]
print("lat_idx range:", lat_idx.min(), lat_idx.max())
print("lon_idx range:", lon_idx.min(), lon_idx.max())
print("num lat:", len(lat_idx), "num lon:", len(lon_idx))
