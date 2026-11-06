import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Open the file
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Define region of interest
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Find indices for the region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

print(f"Region indices - Latitude: {lat_indices[0]} to {lat_indices[-1]}, Longitude: {lon_indices[0]} to {lon_indices[-1]}")

# Get the subset of data for our region
subset = ds.analysed_sst.isel(latitude=lat_indices, longitude=lon_indices)
print(f"Subset shape: {subset.shape}")

# Define target period
target_start = np.datetime64('2003-06-01')
target_end = np.datetime64('2003-08-31')

# Filter for target period
target_mask = (ds.time >= target_start) & (ds.time <= target_end)
target_times = ds.time[target_mask]
print(f"Target period: {target_times[0].values} to {target_times[-1].values}")
print(f"Number of target days: {len(target_times)}")

# Let's also look at baseline period
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

baseline_mask = (ds.time >= baseline_start) & (ds.time <= baseline_end)
baseline_times = ds.time[baseline_mask]
print(f"Baseline period: {baseline_times[0].values} to {baseline_times[-1].values}")
print(f"Number of baseline days: {len(baseline_times)}")

# Close the dataset
ds.close()