import fsspec
import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Correct path based on what we saw
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

# Download the file
fs.get(remote_path, local_path)

# Open the dataset
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define our region and time period
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37
start_date = datetime(2021, 6, 1)
end_date = datetime(2021, 8, 31)

# Select the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Select the time period
ds_time = ds_region.sel(time=slice(start_date, end_date))

print("Region selected:")
print(f"Latitude range: {lat_min} to {lat_max}")
print(f"Longitude range: {lon_min} to {lon_max}")
print(f"Time range: {start_date.date()} to {end_date.date()}")
print(f"Shape of data: {ds_time.analysed_sst.shape}")

# Let's check some basic info about the data
print("\nSample data points:")
print("Time dimension:", ds_time.time.values[:5])
print("Latitude dimension:", ds_time.latitude.values[:5])
print("Longitude dimension:", ds_time.longitude.values[:5])

# Convert SST from Kelvin to Celsius (if needed) - looking at the metadata, it says it's already decoded
# But let's make sure we understand the units
print("\nSST data statistics:")
sst_data = ds_time.analysed_sst.values
print(f"Min SST: {np.nanmin(sst_data):.2f} K")
print(f"Max SST: {np.nanmax(sst_data):.2f} K")
print(f"Mean SST: {np.nanmean(sst_data):.2f} K")
print(f"NaN count: {np.sum(np.isnan(sst_data))}")