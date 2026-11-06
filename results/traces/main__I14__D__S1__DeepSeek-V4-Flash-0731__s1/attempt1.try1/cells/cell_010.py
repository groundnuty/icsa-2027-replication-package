
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region bounds
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

# Find indices
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values

lat_indices = np.where((lat_vals >= lat_min) & (lat_vals <= lat_max))[0]
lon_indices = np.where((lon_vals >= lon_min) & (lon_vals <= lon_max))[0]

print(f"Lat indices: {lat_indices[0]} to {lat_indices[-1]}, count={len(lat_indices)}")
print(f"Lon indices: {lon_indices[0]} to {lon_indices[-1]}, count={len(lon_indices)}")

# Check the actual lat/lon values in the region
print(f"Lat values: {lat_vals[lat_indices[0]]} to {lat_vals[lat_indices[-1]]}")
print(f"Lon values: {lon_vals[lon_indices[0]]} to {lon_vals[lon_indices[-1]]}")

# Time range for baseline with extension
import pandas as pd
baseline_start = pd.Timestamp('1991-12-27')
baseline_end = pd.Timestamp('2003-01-05')
target_start = pd.Timestamp('2015-06-01')
target_end = pd.Timestamp('2015-08-31')

# Get time indices
time_vals = ds.time.values
print(f"Time type: {type(time_vals[0])}")
print(f"Time range in file: {time_vals[0]} to {time_vals[-1]}")

# Check that we have all needed times
print(f"Baseline needed: {baseline_start} to {baseline_end}")
print(f"Target needed: {target_start} to {target_end}")
