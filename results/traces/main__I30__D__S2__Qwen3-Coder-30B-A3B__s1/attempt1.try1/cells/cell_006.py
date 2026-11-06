import fsspec
import xarray as xr
import numpy as np
import os
from datetime import datetime
import json

# Create filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Downloading file...")
fs.get(remote_path, local_path)
print("Download complete")

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define region boundaries
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

# Define target period
target_start = np.datetime64('2010-06-01')
target_end = np.datetime64('2010-08-31')
target_period = slice(target_start, target_end)

# Define baseline period
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# Get the data for our region and target period
def get_region_data(ds, lat_min, lat_max, lon_min, lon_max, time_slice):
    """Extract data for the specified region and time period"""
    # Select region
    region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Select time period
    region_ds = region_ds.sel(time=time_slice)
    
    return region_ds

# Get the data
region_ds = get_region_data(ds, lat_min, lat_max, lon_min, lon_max, target_period)

# Extract SST data
sst_data = region_ds['analysed_sst'].values  # Shape: (days, lat, lon)
latitudes = region_ds.latitude.values
longitudes = region_ds.longitude.values
times = region_ds.time.values

print(f"Region data shape: {sst_data.shape}")
print(f"Latitudes: {latitudes.shape}, range: [{latitudes.min()}, {latitudes.max()}]")
print(f"Longitudes: {longitudes.shape}, range: [{longitudes.min()}, {longitudes.max()}]")
print(f"Times: {times.shape}")

# Helper function to convert datetime64 to day-of-year
def get_doy_for_datetime64(dt64):
    """Convert datetime64 to day-of-year (1-366)"""
    # Convert to datetime object
    dt = dt64.astype(datetime)
    # Get day of year (1-366)
    doy = dt.timetuple().tm_yday
    return doy

# Simplified debugging approach
print("Testing basic functionality...")

# Let's just focus on getting the first few days of baseline data
baseline_mask = (times >= baseline_start) & (times <= baseline_end)
baseline_times = times[baseline_mask]
baseline_sst = sst_data[baseline_mask]

print(f"Baseline period: {baseline_times[0]} to {baseline_times[-1]}")
print(f"Baseline data shape: {baseline_sst.shape}")

# Let's see if we can make a simple test with just a small portion
print("Test - first 10 baseline times:")
for i in range(min(10, len(baseline_times))):
    print(f"  {baseline_times[i]} -> DOY {get_doy_for_datetime64(baseline_times[i])}")

# Now let's manually test our pooling logic for a simple case
print("\nTesting simple pooling for day 60:")

# Create a very small test case to debug
test_sst = np.random.rand(10, 2, 2) * 300  # Simulated SST data (K)
test_times = np.array([np.datetime64('2000-01-01') + np.timedelta64(i, 'D') for i in range(10)])

# Simple test to see if we can make pools
print("Test - trying to understand indexing...")
try:
    doy = 60
    pool = []
    for i, date in enumerate(test_times):
        date_doy = get_doy_for_datetime64(date)
        if abs(date_doy - doy) <= 5:
            # For testing, we just add some dummy values
            pool.extend([1.0, 2.0, 3.0])  # Dummy values
    
    print(f"Pool for DOY {doy}: length {len(pool)}")
    if len(pool) > 0:
        pool_array = np.array(pool, dtype=np.float64)
        valid_pool = pool_array[~np.isnan(pool_array)]
        print(f"Valid pool length: {len(valid_pool)}")
        if len(valid_pool) > 0:
            threshold = np.percentile(valid_pool, 90, method='hazen')
            print(f"Threshold: {threshold}")
except Exception as e:
    print(f"Error in simple test: {e}")

print("\nDebug completed.")