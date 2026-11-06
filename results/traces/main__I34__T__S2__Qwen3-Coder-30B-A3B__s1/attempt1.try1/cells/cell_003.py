import fsspec
import xarray as xr
import numpy as np

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
file_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
print("Dataset dimensions:", dict(ds.dims))
print("Coordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].shape}")
print("\nVariables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].shape}")

# Check the lat/lon range to confirm we're in the right area
print(f"\nLatitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
print(f"Longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")

# Print some sample data
print("\nSample SST data:")
print(ds.analysed_sst.isel(time=0, latitude=0, longitude=0))