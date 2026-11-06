
import fsspec
import xarray as xr
import numpy as np
import datetime
import os

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Define region
lat_min, lat_max = 57.41, 58.61
lon_min, lon_max = 18.69, 19.89

# Load a reference file to get grid info and indices
with fs.open(f'{base}/sst_19920101.nc', 'rb') as fh:
    ds = xr.open_dataset(fh, engine='h5netcdf')
    lat = ds['latitude'].values
    lon = ds['longitude'].values
    ds.close()

lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
print(f'lat_idx: {lat_idx[0]} to {lat_idx[-1]}, count={len(lat_idx)}')
print(f'lon_idx: {lon_idx[0]} to {lon_idx[-1]}, count={len(lon_idx)}')
region_lat = lat[lat_idx]
region_lon = lon[lon_idx]
print(f'Region lat: {region_lat[0]:.4f} to {region_lat[-1]:.4f}')
print(f'Region lon: {region_lon[0]:.4f} to {region_lon[-1]:.4f}')
