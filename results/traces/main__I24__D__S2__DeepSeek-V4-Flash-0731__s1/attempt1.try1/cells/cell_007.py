
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45

lats = ds.latitude.values
lons = ds.longitude.values

lat_idx = np.where((lats >= lat_min) & (lats <= lat_max))[0]
lon_idx = np.where((lons >= lon_min) & (lons <= lon_max))[0]
print("lat_idx", lat_idx, lats[lat_idx[0]], lats[lat_idx[-1]], len(lat_idx))
print("lon_idx", lon_idx, lons[lon_idx[0]], lons[lon_idx[-1]], len(lon_idx))
