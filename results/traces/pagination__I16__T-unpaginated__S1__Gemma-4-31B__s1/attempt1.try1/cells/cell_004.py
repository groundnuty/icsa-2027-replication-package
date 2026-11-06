import numpy as np
import pandas as pd
import xarray as xr
import fsspec
import json
from datetime import datetime, timedelta

# Setup
fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 56.63, 57.83
lon_min, lon_max = 20.23, 21.43
target_start = pd.to_datetime('2008-06-01')
target_end = pd.to_datetime('2008-08-31')
baseline_start = pd.to_datetime('1992-01-01')
baseline_end = pd.to_datetime('2002-12-31')

# Extensions for windows
baseline_ext_start = baseline_start - timedelta(days=5)
baseline_ext_end = baseline_end + timedelta(days=5)

def get_day_of_year(dt):
    # Custom day of year: 1 Jan = 1, ..., 31 Dec = 366.
    # pd.Timestamp.dayofyear is 1-366.
    return dt.dayofyear

# Determine all dates needed
all_needed_dates = set()
# Baseline dates and their windows
# To be safe, we need all dates from baseline_ext_start to baseline_ext_end
curr = baseline_ext_start
while curr <= baseline_ext_end:
    all_needed_dates.add(curr)
    curr += timedelta(days=1)

# Target dates
curr = target_start
while curr <= target_end:
    all_needed_dates.add(curr)
    curr += timedelta(days=1)

# Filter files that exist and match these dates
# Files are named sst_YYYYMMDD.nc
needed_files = []
for dt in all_needed_dates:
    filename = f"sst_{dt.strftime('%Y%m%d')}.nc"
    path = f"{base_path}/{filename}"
    # Check if file exists. fs.ls() might be slow, but we can't avoid it if we don't know the files.
    # Better: list all files once and filter.
    pass

# Listing all files once
all_files = fs.ls(base_path)
all_files_set = set(all_files)

needed_files = []
for dt in all_needed_dates:
    filename = f"sst_{dt.strftime('%Y%m%d')}.nc"
    path = f"{base_path}/{filename}"
    if path in all_files_set:
        needed_files.append(path)

# Load SST for the region
# We'll load them one by one and slice them to save memory.
# Let's find the coordinate indices first.
with fs.open(all_files[0], 'rb') as f:
    ds_sample = xr.open_dataset(f, engine='h5netcdf')
    lat_idx = np.where((ds_sample.latitude >= lat_min) & (ds_sample.latitude <= lat_max))[0]
    lon_idx = np.where((ds_sample.longitude >= lon_min) & (ds_sample.longitude <= lon_max))[0]
    lats = ds_sample.latitude.values[lat_idx]
    lons = ds_sample.longitude.values[lon_idx]
    
# Now load data for all needed dates
data_list = []
dates_list = []

# Sort needed_files to have dates in order?
# Let's just collect and then sort.
# The list 'all_needed_dates' is already a set, let's use a sorted list.
sorted_needed_dates = sorted(list(all_needed_dates))

for dt in sorted_needed_dates:
    filename = f"sst_{dt.strftime('%Y%m%d')}.nc"
    path = f"{base_path}/{filename}"
    if path in all_files_set:
        with fs.open(path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            # Slice the region
            sst_slice = ds.analysed_sst.isel(latitude=slice(lat_idx[0], lat_idx[-1]+1), 
                                             longitude=slice(lon_idx[0], lon_idx[-1]+1))
            data_list.append(sst_slice.values[0]) # time dim is 1
            dates_list.append(dt)

sst_array = np.array(data_list, dtype='float64') # (time, lat, lon)
sst_dates = np.array(dates_list)

print(f"Loaded SST array shape: {sst_array.shape}")
print(f"Loaded dates range: {sst_dates[0]} to {sst_dates[-1]}")
