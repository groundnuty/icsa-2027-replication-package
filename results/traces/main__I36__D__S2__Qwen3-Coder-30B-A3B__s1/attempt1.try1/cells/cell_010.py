import xarray as xr
import numpy as np
import os
import pandas as pd

# Load the dataset
local_path = '/work/sst_s2.nc'
ds = xr.open_dataset(local_path, engine="h5netcdf")

# Define our region boundaries
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Find indices for our region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

# Extract the region data
region_sst = ds['analysed_sst'].isel(latitude=lat_indices, longitude=lon_indices)
region_lat = ds.latitude.isel(latitude=lat_indices)
region_lon = ds.longitude.isel(longitude=lon_indices)

# Target period: 2003-06-01 to 2003-08-31
target_start = np.datetime64('2003-06-01')
target_end = np.datetime64('2003-08-31')

# Get all time indices for the target period
target_times = np.where((ds.time >= target_start) & (ds.time <= target_end))[0]

# Extract target data
target_sst_subset = ds['analysed_sst'].isel(time=target_times, latitude=lat_indices, longitude=lon_indices)

print("Analyzing target SST data to verify it contains valid values...")
print(f"Target SST subset shape: {target_sst_subset.shape}")

# Check a few sample values
sample_sst = target_sst_subset.isel(time=0).values
print(f"Sample SST values (first 5x5): {sample_sst[:5, :5]}")

# Check if any values are finite
finite_count = np.count_nonzero(np.isfinite(sample_sst))
print(f"Finite SST values in first day: {finite_count} out of {sample_sst.size}")

# Check min/max of SST in the region for the target period
print("Checking SST range in target period...")
min_sst = target_sst_subset.min(skipna=True).values
max_sst = target_sst_subset.max(skipna=True).values
print(f"Min SST in region: {min_sst}")
print(f"Max SST in region: {max_sst}")

# Check a few days for comparison
print("\nChecking SST for several days:")
for i in [0, 10, 20, 30]:
    if i < len(target_sst_subset.time):
        day_sst = target_sst_subset.isel(time=i).values
        day_finite = np.count_nonzero(np.isfinite(day_sst))
        day_min = np.nanmin(day_sst)
        day_max = np.nanmax(day_sst)
        print(f"Day {i}: {day_finite} finite values, min={day_min:.2f}, max={day_max:.2f}")

print("\nDone checking SST data.")