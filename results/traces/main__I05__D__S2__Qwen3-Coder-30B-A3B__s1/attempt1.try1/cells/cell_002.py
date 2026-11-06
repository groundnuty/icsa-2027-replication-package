import fsspec
import xarray as xr
import numpy as np

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

fs.get(remote_path, local_path)

# Open the dataset
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Examine the SST data
print("SST variable details:")
print(ds['analysed_sst'])

# Check coordinate ranges
print("\nLatitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
print("Time range:", ds.time.min().values, "to", ds.time.max().values)

# Let's also look at some sample data
print("\nSample SST data (first few time steps):")
print(ds.analysed_sst.isel(time=slice(0, 5)).values)