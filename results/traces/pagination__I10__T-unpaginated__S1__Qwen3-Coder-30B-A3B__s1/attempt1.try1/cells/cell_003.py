import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')

# Let's look at a few files to understand the pattern
file_paths = [
    '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc',
    '/icsa2027_data_20261101T090944Z/s1z/sst_19820102.nc',
    '/icsa2027_data_20261101T090944Z/s1z/sst_19920101.nc',
    '/icsa2027_data_20261101T090944Z/s1z/sst_20050601.nc'
]

for path in file_paths:
    try:
        with fs.open(path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            print(f"File: {path}")
            print(f"  Time: {ds['time'].values}")
            print(f"  SST shape: {ds['analysed_sst'].shape}")
            print(f"  Lat range: {ds['latitude'].min().values} to {ds['latitude'].max().values}")
            print(f"  Lon range: {ds['longitude'].min().values} to {ds['longitude'].max().values}")
            print()
    except Exception as e:
        print(f"Error reading {path}: {e}")
        break