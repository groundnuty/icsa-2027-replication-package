import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta

# Create directories
os.makedirs('output', exist_ok=True)
os.makedirs('temp', exist_ok=True)

# Get a subset of files for the baseline period (1992-2002) - but we don't have this data!
# We'll need to work with what we have, likely from the 1980s.

# Let's check if we have any files in 2013 for the target period
fs = fsspec.filesystem('onedata')
files = fs.ls('/icsa2027_data_20261101T090944Z/s1z')
date_pattern = r'sst_(\d{8})\.nc'

# Filter files for 2013
files_2013 = [f for f in files if 'sst_2013' in f]
print(f"Files from 2013: {len(files_2013)}")

# Check if we have any files from 1990s
files_1990s = [f for f in files if 'sst_199' in f]
print(f"Files from 1990s: {len(files_1990s)}")

# Since we don't have the required data periods, we'll need to work with what we have
# But for now, let's look at the structure of a file from 1982 to understand the data
remote_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_path = 'temp/sst_19820101.nc'
fs.get(remote_path, local_path)

# Load the dataset
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset coordinates:")
print(f"Latitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
print(f"Longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")

# Define our region of interest
lat_min, lat_max = 57.41, 58.61
lon_min, lon_max = 18.69, 19.89

# Find indices for our region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

print(f"\nRegion indices - Lat: {lat_indices[0]} to {lat_indices[-1]}, Lon: {lon_indices[0]} to {lon_indices[-1]}")
print(f"Region shape: {len(lat_indices)} x {len(lon_indices)}")

# Show actual coordinates for our region
if len(lat_indices) > 0 and len(lon_indices) > 0:
    region_lat = ds.latitude.isel(latitude=lat_indices)
    region_lon = ds.longitude.isel(longitude=lon_indices)
    print(f"Actual region coordinates:")
    print(f"Lat: {region_lat.values[0]} to {region_lat.values[-1]}")
    print(f"Lon: {region_lon.values[0]} to {region_lon.values[-1]}")
    
# Close the dataset
ds.close()