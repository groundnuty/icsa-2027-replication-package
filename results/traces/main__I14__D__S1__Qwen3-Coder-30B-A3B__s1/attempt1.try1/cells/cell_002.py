import xarray as xr
import fsspec
import os

# Download one file to examine its structure
fs = fsspec.filesystem('onedata')
remote_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_path = '/work/sst_19820101.nc'
fs.get(remote_path, local_path)

# Open with xarray to see the structure
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset coordinates:")
print(ds.coords)
print("\nDataset variables:")
print(ds.data_vars)
print("\nSST variable details:")
print(ds['sst'])