import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# First let me examine a sample file to understand the structure
fs = fsspec.filesystem('onedata')
sample_file = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'

# Open a sample file to see the structure
with fs.open(sample_file, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Sample file structure:")
    print(ds)
    print("\nCoordinates:")
    print(ds.coords)
    print("\nVariables:")
    print(ds.data_vars)
    
    # Check if we have lat/lon coordinates
    if 'lat' in ds.coords and 'lon' in ds.coords:
        print(f"\nLat range: {ds.lat.min().values} to {ds.lat.max().values}")
        print(f"Lon range: {ds.lon.min().values} to {ds.lon.max().values}")
        print(f"Shape: {ds.sst.shape}")