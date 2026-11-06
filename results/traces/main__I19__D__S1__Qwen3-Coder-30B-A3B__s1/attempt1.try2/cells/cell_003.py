import xarray as xr
import numpy as np
import fsspec

# Examine the actual variable structure
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
print("\nAnalysed SST variable shape:", ds['analysed_sst'].shape)
print("Analysed SST variable dims:", ds['analysed_sst'].dims)
print("\nFirst few latitudes:", ds['latitude'][:5].values)  # Show first 5 latitudes
print("First few longitudes:", ds['longitude'][:5].values)  # Show first 5 longitudes
print("\nSample SST data (first 3x3):")
print(ds['analysed_sst'][0, :3, :3].values)