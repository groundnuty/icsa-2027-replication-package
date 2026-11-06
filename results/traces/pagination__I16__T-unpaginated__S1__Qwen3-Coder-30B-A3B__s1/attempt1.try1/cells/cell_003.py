import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')

# Examine the data structure more carefully
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    print("\nAnalysed SST variable shape:", ds['analysed_sst'].shape)
    print("Latitudes range:", ds['latitude'].min().values, "to", ds['latitude'].max().values)
    print("Longitudes range:", ds['longitude'].min().values, "to", ds['longitude'].max().values)
    
    # Check a small subset of data
    print("\nSample SST data (first few points):")
    sst_sample = ds['analysed_sst'][0, :3, :3]  # First time, first 3 lat, first 3 lon
    print(sst_sample.values)