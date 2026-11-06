import fsspec
import xarray as xr
import os

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Downloading file...")
fs.get(remote_path, local_path)
print("Download completed.")

# Open with xarray to examine structure
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("\nDataset structure:")
print(ds)

print("\nVariables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}")

print("\nDimensions:")
for dim in ds.dims:
    print(f"  {dim}: {ds.dims[dim]}")

print("\nCoordinates:")
for coord in ds.coords:
    print(f"  {coord}: {ds[coord].shape}")

# Check the lat/lon ranges
if 'latitude' in ds.coords:
    print(f"\nLatitude range: {ds['latitude'].min().values} to {ds['latitude'].max().values}")
if 'longitude' in ds.coords:
    print(f"Longitude range: {ds['longitude'].min().values} to {ds['longitude'].max().values}")

# Check time range
if 'time' in ds.coords:
    print(f"\nTime range: {ds['time'].min().values} to {ds['time'].max().values}")
    
# Close the dataset
ds.close()