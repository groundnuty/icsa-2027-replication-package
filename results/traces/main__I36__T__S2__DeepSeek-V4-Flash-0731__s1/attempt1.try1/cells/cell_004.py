
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

lats = ds.latitude.values
lons = ds.longitude.values

lat_mask = (lats >= lat_min) & (lats <= lat_max)
lon_mask = (lons >= lon_min) & (lons <= lon_max)

print("Lat mask count:", lat_mask.sum())
print("Lon mask count:", lon_mask.sum())
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("Lat indices:", lat_idx[0], "to", lat_idx[-1])
print("Lon indices:", lon_idx[0], "to", lon_idx[-1])
print("Lat values:", lats[lat_idx[0]], lats[lat_idx[-1]])
print("Lon values:", lons[lon_idx[0]], lons[lon_idx[-1]])
