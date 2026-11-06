
import xarray as xr
import numpy as np

ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values

# Find indices for region: lat 57.85-59.05, lon 21.01-22.21
lat_mask = (lat >= 57.85) & (lat <= 59.05)
lon_mask = (lon >= 21.01) & (lon <= 22.21)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
print("lat values:", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
print("lon values:", lon[lon_idx[0]], lon[lon_idx[-1]])

# Check the data values in the region
print(ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1])
