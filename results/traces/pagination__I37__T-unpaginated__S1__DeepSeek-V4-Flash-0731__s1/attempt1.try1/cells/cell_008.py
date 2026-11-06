
import fsspec
import xarray as xr
import numpy as np
import datetime

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Get region indices
f = fs.open(f'{base}/sst_20120601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
lat_idx = np.where((lats >= 60.09) & (lats <= 61.29))[0]
lon_idx = np.where((lons >= 20.01) & (lons <= 21.21))[0]
print(f"Lat indices: {lat_idx[0]}-{lat_idx[-1]} ({len(lat_idx)})")
print(f"Lon indices: {lon_idx[0]}-{lon_idx[-1]} ({len(lon_idx)})")
print(f"Lat values: {lats[lat_idx[0]]} to {lats[lat_idx[-1]]}")
print(f"Lon values: {lons[lon_idx[0]]} to {lons[lon_idx[-1]]}")
