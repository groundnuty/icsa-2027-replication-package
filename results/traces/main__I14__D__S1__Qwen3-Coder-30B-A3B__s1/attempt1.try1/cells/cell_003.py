import xarray as xr
import fsspec
import os

# Check the time range of the dataset
fs = fsspec.filesystem('onedata')
# Get a few files to check the time range
files = fs.glob('/icsa2027_data_20261101T090944Z/s1z/sst_*.nc')
print("Number of files:", len(files))
print("First few files:", files[:5])

# Check the time range
first_file = files[0]
ds = xr.open_dataset(fs.open(first_file), engine='h5netcdf')
print("First file time:", ds.time.values)
ds.close()

last_file = files[-1]
ds = xr.open_dataset(fs.open(last_file), engine='h5netcdf')
print("Last file time:", ds.time.values)
ds.close()