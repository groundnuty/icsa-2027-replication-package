import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Setup filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define our region and time period
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
start_date = datetime(2021, 6, 1)
end_date = datetime(2021, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Filter to region
region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Filter to time period
region_ds = region_ds.sel(time=slice(start_date, end_date))
baseline_ds = ds.sel(time=slice(baseline_start, baseline_end))

print(f"Region dimensions: {region_ds.dims}")
print(f"Region shape: {region_ds['analysed_sst'].shape}")
print(f"Baseline shape: {baseline_ds['analysed_sst'].shape}")

# Show the actual time ranges
print(f"Target period: {region_ds.time.min().values} to {region_ds.time.max().values}")
print(f"Baseline period: {baseline_ds.time.min().values} to {baseline_ds.time.max().values}")

# Check how many days we have in target period
print(f"Number of days in target period: {len(region_ds.time)}")

# Check how many days we have in baseline period
print(f"Number of days in baseline period: {len(baseline_ds.time)}")