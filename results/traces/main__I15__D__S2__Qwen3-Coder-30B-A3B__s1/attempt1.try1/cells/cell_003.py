import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Open the dataset
local_path = '/work/sst_s2.nc'
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define the region of interest
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

# Extract the region
region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define the target period
start_date = datetime(2019, 6, 1)
end_date = datetime(2019, 8, 31)

# Filter the time period
region_ds = region_ds.sel(time=slice(start_date, end_date))

print("Region dimensions:")
print(f"  Latitude: {region_ds.latitude.min().values} to {region_ds.latitude.max().values}")
print(f"  Longitude: {region_ds.longitude.min().values} to {region_ds.longitude.max().values}")
print(f"  Time: {region_ds.time.min().values} to {region_ds.time.max().values}")

# Get the SST data
sst_data = region_ds['analysed_sst']

print(f"\nSST data shape: {sst_data.shape}")
print(f"SST data dtype: {sst_data.dtype}")

# Check some sample values
print(f"\nSample SST values (first few):")
print(sst_data.isel(time=0, latitude=0, longitude=0).values)
print(sst_data.isel(time=0, latitude=1, longitude=1).values)

# Close the dataset
ds.close()
region_ds.close()