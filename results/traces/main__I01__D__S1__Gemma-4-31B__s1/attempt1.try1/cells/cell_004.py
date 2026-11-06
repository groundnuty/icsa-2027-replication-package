import fsspec
import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'

# Coordinates of the region
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87

# Target and Baseline periods
target_start = pd.Timestamp('2008-06-01')
target_end = pd.Timestamp('2008-08-31')
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')

# Windows extension
extended_baseline_start = baseline_start - pd.Timedelta(days=5)
extended_baseline_end = baseline_end + pd.Timedelta(days=5)

def get_date_str(dt):
    return dt.strftime('%Y%m%d')

# Generate required dates
all_baseline_dates = pd.date_range(extended_baseline_start, extended_baseline_end)
all_target_dates = pd.date_range(target_start, target_end)

baseline_files = [f"{path}/sst_{get_date_str(d)}.nc" for d in all_baseline_dates]
target_files = [f"{path}/sst_{get_date_str(d)}.nc" for d in all_target_dates]

# Check if all files exist
all_needed_files = baseline_files + target_files
existing_files = fs.ls(path)
# The fs.ls returned paths like 'icsa2027_data_20261101T090944Z/s1z/sst_...nc'
# Let's verify
missing_files = [f for f in all_needed_files if f not in existing_files]
print(f"Missing files: {len(missing_files)}")
if missing_files:
    print(f"First 5 missing: {missing_files[:5]}")

# Get coordinates from one file to slice the region
sample_file_remote = target_files[0]
sample_file_local = f'/work/{os.path.basename(sample_file_remote)}'
fs.get(sample_file_remote, sample_file_local)
ds = xr.open_dataset(sample_file_local, engine="h5netcdf")
print(ds)
# Extract coords
lats = ds.lat.values
lons = ds.lon.values
ds.close()
os.remove(sample_file_local)

# Find indices for the region
lat_idx = np.where((lats >= lat_min) & (lats <= lat_max))[0]
lon_idx = np.where((lons >= lon_min) & (lons <= lon_max))[0]
print(f"Lat indices: {lat_idx}, Lon indices: {lon_idx}")
