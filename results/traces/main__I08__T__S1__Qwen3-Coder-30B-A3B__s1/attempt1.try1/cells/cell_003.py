import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')

# Let's examine a few files to understand the time range
file_paths = [
    '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc',
    '/icsa2027_data_20261101T090944Z/s1z/sst_19900101.nc',
    '/icsa2027_data_20261101T090944Z/s1z/sst_20000101.nc',
    '/icsa2027_data_20261101T090944Z/s1z/sst_20070101.nc'
]

for file_path in file_paths:
    try:
        with fs.open(file_path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            print(f"File {file_path.split('/')[-1]}:")
            print(f"  Time: {ds.time.values}")
            print()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")