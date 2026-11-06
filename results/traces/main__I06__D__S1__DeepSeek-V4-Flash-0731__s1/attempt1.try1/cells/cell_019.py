
import numpy as np
import xarray as xr

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values

lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25

lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]

print(f"lat_idx range: {lat_idx[0]} to {lat_idx[-1]}, count: {len(lat_idx)}")
print(f"lat values: {lat[lat_idx[0]]} to {lat[lat_idx[-1]]}")
print(f"lon_idx range: {lon_idx[0]} to {lon_idx[-1]}, count: {len(lon_idx)}")
print(f"lon values: {lon[lon_idx[0]]} to {lon[lon_idx[-1]]}")
