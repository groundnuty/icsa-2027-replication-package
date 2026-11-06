
import fsspec
import xarray as xr
import numpy as np
import datetime as dt
import os

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

# Define region
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

# First, read one file to get lat/lon indices
f = fs.open(f'{base_path}/sst_19820101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
ds.close()
print(f"lat_idx: {len(lat_idx)}, range {lat_idx[0]}-{lat_idx[-1]}")
print(f"lon_idx: {len(lon_idx)}, range {lon_idx[0]}-{lon_idx[-1]}")
print(f"Selected lat: {lat[lat_idx[0]]} to {lat[lat_idx[-1]]}")
print(f"Selected lon: {lon[lon_idx[0]]} to {lon[lon_idx[-1]]}")
