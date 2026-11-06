import fsspec
import xarray as xr
import numpy as np
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = 'icsa2027_data_220261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Downloading file...")
fs.get(remote_path, local_path)
print("Download complete.")

# Open the dataset
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset opened successfully.")
print(ds)

# Let's look at the coordinates and variables
print("\nCoordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].values[:5] if len(ds[coord]) > 5 else ds[coord].values}")

print("\nVariables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}")