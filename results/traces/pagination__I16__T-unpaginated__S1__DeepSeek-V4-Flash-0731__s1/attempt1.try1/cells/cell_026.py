
import fsspec
import xarray as xr
import numpy as np

# Get the actual latitude and longitude values from the dataset
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat_full = ds['latitude'].values
lon_full = ds['longitude'].values

# Region indices
lat_idx = np.arange(157, 217)  # 60 cells
lon_idx = np.arange(562, 622)  # 60 cells

region_lat = lat_full[lat_idx]
region_lon = lon_full[lon_idx]

print('Region latitude values:', region_lat)
print('Region longitude values:', region_lon)
print('Lat range:', region_lat.min(), region_lat.max())
print('Lon range:', region_lon.min(), region_lon.max())

# Verify bounds
print('Lat within [56.63, 57.83]:', np.all((region_lat >= 56.63) & (region_lat <= 57.83)))
print('Lon within [20.23, 21.43]:', np.all((region_lon >= 20.23) & (region_lon <= 21.43)))

# Get target time values
print('Time:', ds['time'].values)
