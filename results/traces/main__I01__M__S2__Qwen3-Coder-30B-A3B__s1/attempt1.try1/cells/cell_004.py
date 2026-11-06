import xarray as xr
import numpy as np
from datetime import datetime

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Define our region of interest
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87

# Find indices for our region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

# Extract the subset for our analysis
subset = ds.isel(latitude=lat_indices, longitude=lon_indices)

# Define our target period
target_start = np.datetime64('2008-06-01')
target_end = np.datetime64('2008-08-31')

# Get all time indices within our target period
time_indices = np.where((subset.time >= target_start) & (subset.time <= target_end))[0]

print(f"Target period: {target_start} to {target_end}")
print(f"Number of days in target period: {len(time_indices)}")

# Get baseline period (1992-2002)
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# Get all time indices within baseline period
baseline_indices = np.where((subset.time >= baseline_start) & (subset.time <= baseline_end))[0]

print(f"Baseline period: {baseline_start} to {baseline_end}")
print(f"Number of days in baseline period: {len(baseline_indices)}")

# Extract data for baseline period
baseline_data = subset.analysed_sst.isel(time=baseline_indices).values

# Extract data for target period  
target_data = subset.analysed_sst.isel(time=time_indices).values

print(f"Baseline data shape: {baseline_data.shape}")
print(f"Target data shape: {target_data.shape}")

# Convert to Kelvin (as mentioned in the instructions)
# The data seems to already be in Kelvin based on the sample values (~277K)
# But let's verify the units to make sure

print(f"Sample baseline SST values: {baseline_data[0, 0, 0]:.2f} K")
print(f"Sample target SST values: {target_data[0, 0, 0]:.2f} K")