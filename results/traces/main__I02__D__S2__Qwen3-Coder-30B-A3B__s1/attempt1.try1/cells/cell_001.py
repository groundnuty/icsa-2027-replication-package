import fsspec
import xarray as xr
import os

# Setup the filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Downloading file...")
fs.get(remote_path, local_path)
print("Download completed.")

# Open with xarray
print("Opening dataset...")
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset opened successfully.")

# Print basic info about the dataset
print("\nDataset dimensions:")
print(ds.dims)
print("\nDataset variables:")
print(ds.data_vars)
print("\nDataset coordinates:")
print(ds.coords)

# Check what variables we have
print("\nVariables in dataset:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}")
    
# Check coordinate ranges
if 'lat' in ds.coords:
    print(f"\nLatitude range: {ds.lat.min().values} to {ds.lat.max().values}")
if 'lon' in ds.coords:
    print(f"Longitude range: {ds.lon.min().values} to {ds.lon.max().values}")
if 'time' in ds.coords:
    print(f"Time range: {ds.time.min().values} to {ds.time.max().values}")