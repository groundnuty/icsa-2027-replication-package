import xarray as xr
import fsspec
import os
import numpy as np

# Create a temporary directory for downloading files
os.makedirs('/work', exist_ok=True)

# Download and examine one file to understand the structure
fs = fsspec.filesystem('onedata')
remote_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_path = '/work/test.nc'

fs.get(remote_path, local_path)
ds = xr.open_dataset(local_path, engine='h5netcdf')

print("Dataset coordinates:")
print(ds.coords)
print("\nDataset variables:")
print(ds.data_vars)
print("\nAnalysed SST variable details:")
print(ds['analysed_sst'])
print("\nLat/Lon ranges:")
print("Latitude range:", ds['latitude'].min().values, "to", ds['latitude'].max().values)
print("Longitude range:", ds['longitude'].min().values, "to", ds['longitude'].max().values)

# Check a small subset of data
print("\nSample data (first few points):")
print(ds['analysed_sst'].isel(time=0, latitude=0, longitude=0).values)