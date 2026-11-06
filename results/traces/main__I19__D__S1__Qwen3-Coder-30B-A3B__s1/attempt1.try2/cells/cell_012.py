import datetime
import numpy as np
import xarray as xr
import fsspec
import os

# First, let's make sure we can download and read the files properly
fs = fsspec.filesystem('onedata')

# Let's download and examine a few files from the available years to understand the data
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
print(f"Total files: {len(files)}")

# Download first few files to analyze
sample_files = files[:5]
for i, remote_path in enumerate(sample_files):
    filename = remote_path.split('/')[-1]
    local_path = f'/tmp/{filename}'
    fs.get(remote_path, local_path)
    print(f"Downloaded: {filename}")

# Now let's see if we can find the region of interest
# Let's load one file and examine the coordinates
local_sample = '/tmp/sst_19820101.nc'
ds = xr.open_dataset(local_sample, engine='h5netcdf')

print("\nCoordinate ranges in sample file:")
print(f"Latitude range: {ds['latitude'].min().values} to {ds['latitude'].max().values}")
print(f"Longitude range: {ds['longitude'].min().values} to {ds['longitude'].max().values}")

# Check if our target region falls within these bounds
target_lat_min = 57.13
target_lat_max = 58.33
target_lon_min = 22.79
target_lon_max = 23.99

lat_in_bounds = (ds['latitude'].min().values <= target_lat_min and 
                 ds['latitude'].max().values >= target_lat_max)
lon_in_bounds = (ds['longitude'].min().values <= target_lon_min and 
                 ds['longitude'].max().values >= target_lon_max)

print(f"\nTarget region bounds:")
print(f"Lat: {target_lat_min} to {target_lat_max}")
print(f"Lon: {target_lon_min} to {target_lon_max}")
print(f"Latitude bounds covered: {lat_in_bounds}")
print(f"Longitude bounds covered: {lon_in_bounds}")

# Let's also check the actual data values in the region
print("\nSample data in target region:")
# Find indices for our region
lat_indices = np.where((ds['latitude'] >= target_lat_min) & (ds['latitude'] <= target_lat_max))[0]
lon_indices = np.where((ds['longitude'] >= target_lon_min) & (ds['longitude'] <= target_lon_max))[0]

print(f"Lat indices in region: {lat_indices[:5]}...{lat_indices[-5:] if len(lat_indices) > 10 else lat_indices}")
print(f"Lon indices in region: {lon_indices[:5]}...{lon_indices[-5:] if len(lon_indices) > 10 else lon_indices}")

if len(lat_indices) > 0 and len(lon_indices) > 0:
    # Take a small sample of the data
    sample_lat_idx = lat_indices[0]
    sample_lon_idx = lon_indices[0]
    print(f"\nSample SST at first region point: {ds['analysed_sst'].values[0, sample_lat_idx, sample_lon_idx]}")
else:
    print("No intersection found with target region")

# Let's also examine the time dimension
print(f"\nTime dimension: {ds['time'].values}")