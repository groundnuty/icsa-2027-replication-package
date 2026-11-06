
import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values

# Find region indices
lat_idx = np.where((lat >= 56.63) & (lat <= 57.83))[0]
lon_idx = np.where((lon >= 20.23) & (lon <= 21.43))[0]
print("lat idx range:", lat_idx[0], lat_idx[-1], "count", len(lat_idx))
print("lon idx range:", lon_idx[0], lon_idx[-1], "count", len(lon_idx))
print("lat values:", lat[lat_idx])
print("lon values:", lon[lon_idx])
