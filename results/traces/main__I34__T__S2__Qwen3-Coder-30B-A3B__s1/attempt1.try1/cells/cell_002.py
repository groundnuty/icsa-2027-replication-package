import fsspec
import xarray as xr
import numpy as np

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
file_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
print("Dataset dimensions:", ds.dims)
print("Coordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].shape}")
print("\nVariables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].shape}")

# Check the lat/lon range to confirm we're in the right area
print(f"\nLatitude range: {ds.lat.min().values} to {ds.lat.max().values}")
print(f"Longitude range: {ds.lon.min().values} to {ds.lon.max().values}")