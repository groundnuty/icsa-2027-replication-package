
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values
print('lat range:', lat.min(), lat.max())
print('lon range:', lon.min(), lon.max())
# Find indices for region
lat_sel = np.where((lat >= 56.63) & (lat <= 57.83))[0]
lon_sel = np.where((lon >= 20.23) & (lon <= 21.43))[0]
print('lat indices:', lat_sel[0], lat_sel[-1], 'count:', len(lat_sel))
print('lon indices:', lon_sel[0], lon_sel[-1], 'count:', len(lon_sel))
print('lat values in range:', lat[lat_sel])
print('lon values in range:', lon[lon_sel])
