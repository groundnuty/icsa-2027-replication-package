
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Region: lat 59.05 to 60.25, lon 21.25 to 22.45
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45

# Find indices
lat_idx = np.where((ds.latitude.values >= lat_min) & (ds.latitude.values <= lat_max))[0]
lon_idx = np.where((ds.longitude.values >= lon_min) & (ds.longitude.values <= lon_max))[0]
print("lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
print("lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
print("lat values:", ds.latitude.values[lat_idx[0]], ds.latitude.values[lat_idx[-1]])
print("lon values:", ds.longitude.values[lon_idx[0]], ds.longitude.values[lon_idx[-1]])
