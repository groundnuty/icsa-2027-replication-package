import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Setup the filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_220261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Downloading file...")
fs.get(remote_path, local_path)
print("Download completed.")

# Open with xarray
print("Opening dataset...")
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset opened successfully.")

# Define our region of interest
lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45

# Filter to our region
print("Filtering to region...")
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
print(f"Region dimensions: {ds_region.dims}")

# Define our target period
start_date = datetime(2004, 6, 1)
end_date = datetime(2004, 8, 31)

# Filter to target period
print("Filtering to target period...")
ds_period = ds_region.sel(time=slice(start_date, end_date))
print(f"Period dimensions: {ds_period.dims}")

# Get the SST data
sst_data = ds_period['analysed_sst']

print(f"SST data shape: {sst_data.shape}")
print(f"Time range in filtered data: {sst_data.time.min().values} to {sst_data.time.max().values}")

# Show first few time steps
print("First few time steps:")
print(sst_data.time.values[:5])

# Let's also look at some sample data points
print("\nSample SST values (first 3x3 grid points):")
sample_sst = sst_data.isel(time=0).values[:3, :3]
print(sample_sst)