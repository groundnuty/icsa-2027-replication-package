import xarray as xr
import numpy as np
import fsspec

# First let's look at a sample file to understand the structure
fs = fsspec.filesystem('onedata')
sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_path = '/tmp/sample.nc'

# Download one file to examine its structure
fs.get(sample_file, local_path)

# Open and examine
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset coordinates:")
print(ds.coords)
print("\nDataset variables:")
print(ds.data_vars)
print("\nSST variable shape:", ds['sst'].shape)
print("SST variable dims:", ds['sst'].dims)
print("\nLatitudes:", ds['latitude'][:5].values)  # Show first 5 latitudes
print("Longitudes:", ds['longitude'][:5].values)  # Show first 5 longitudes