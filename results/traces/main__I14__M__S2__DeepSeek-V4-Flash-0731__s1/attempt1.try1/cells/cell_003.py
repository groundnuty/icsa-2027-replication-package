
import xarray as xr
import numpy as np
import os

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

lat_idx = np.where((ds.latitude.values >= lat_min) & (ds.latitude.values <= lat_max))[0]
lon_idx = np.where((ds.longitude.values >= lon_min) & (ds.longitude.values <= lon_max))[0]

# Load the region data
sst = ds.analysed_sst.isel(latitude=lat_idx, longitude=lon_idx)
print(sst.shape)
print(sst.dtype)

# Check time values
times = ds.time.values
print(times[:5])
print(times[-5:])
