import fsspec
import xarray as xr
import numpy as np
import os

# Create filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Downloading file...")
fs.get(remote_path, local_path)
print("Download complete")

# Open with xarray
print("Opening dataset...")
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset opened successfully")

# Print detailed information
print("\nDataset dimensions:", dict(ds.sizes))
print("\nCoordinates:")
for coord in ds.coords:
    print(f"  {coord}: shape={ds[coord].shape}, values range=[{ds[coord].min().values}, {ds[coord].max().values}]")

# Check variable details
print("\nVariables:")
for var in ds.data_vars:
    print(f"  {var}: shape={ds[var].shape}, dtype={ds[var].dtype}")

# Let's examine the actual coordinate names
print("\nActual coordinate names:")
print(list(ds.coords.keys()))

# Check latitude and longitude specifically
lat_var = None
lon_var = None
for coord in ds.coords:
    if 'lat' in coord.lower():
        lat_var = coord
    elif 'lon' in coord.lower():
        lon_var = coord

print(f"\nLatitude variable: {lat_var}")
print(f"Longitude variable: {lon_var}")

if lat_var:
    print(f"Latitude range: {ds[lat_var].min().values} to {ds[lat_var].max().values}")
    print(f"Latitude shape: {ds[lat_var].shape}")
if lon_var:
    print(f"Longitude range: {ds[lon_var].min().values} to {ds[lon_var].max().values}")
    print(f"Longitude shape: {ds[lon_var].shape}")

# Check time range
print(f"\nTime range: {ds.time.min().values} to {ds.time.max().values}")
print(f"Time shape: {ds.time.shape}")

# Let's also see how many days we have in our target period
target_start = np.datetime64('2010-06-01')
target_end = np.datetime64('2010-08-31')
print(f"\nTarget period: {target_start} to {target_end}")

# Filter time to our target period
target_times = ds.time.where((ds.time >= target_start) & (ds.time <= target_end), drop=True)
print(f"Number of days in target period: {len(target_times)}")