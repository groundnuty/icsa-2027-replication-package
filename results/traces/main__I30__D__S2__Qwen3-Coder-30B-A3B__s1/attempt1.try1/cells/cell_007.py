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

# Let's look at the full time range to understand better
print("Full time range in dataset:")
print(f"Min time: {ds.time.min().values}")
print(f"Max time: {ds.time.max().values}")
print(f"Total time points: {len(ds.time)}")

# Check what happens with the slicing
print("\nChecking target period:")
target_start = np.datetime64('2010-06-01')
target_end = np.datetime64('2010-08-31')
print(f"Target start: {target_start}")
print(f"Target end: {target_end}")

# Let's see what we get from our selection
print("\nSelecting target period from full dataset...")
try:
    # First, let's select the full time range to see what we're working with
    selected_times = ds.time.where((ds.time >= target_start) & (ds.time <= target_end), drop=True)
    print(f"Selected target times count: {len(selected_times)}")
    print(f"Selected times range: {selected_times[0].values} to {selected_times[-1].values}")
    
    # Check the full baseline range too
    baseline_start = np.datetime64('1992-01-01')
    baseline_end = np.datetime64('2002-12-31')
    print(f"\nBaseline range: {baseline_start} to {baseline_end}")
    
    baseline_times = ds.time.where((ds.time >= baseline_start) & (ds.time <= baseline_end), drop=True)
    print(f"Baseline times count: {len(baseline_times)}")
    print(f"Baseline times range: {baseline_times[0].values} to {baseline_times[-1].values}")
    
    # Now try to actually extract the region data
    lat_min, lat_max = 58.69, 59.89
    lon_min, lon_max = 18.69, 19.89
    
    print(f"\nSelecting region: lat[{lat_min}:{lat_max}], lon[{lon_min}:{lon_max}]")
    
    # Select region first
    region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    print(f"Region dimensions: {region_ds.dims}")
    
    # Then select time period
    region_ds = region_ds.sel(time=target_period)
    print(f"After time selection: {region_ds.dims}")
    
    # Check if we got data
    if 'analysed_sst' in region_ds.data_vars:
        print(f"SST data shape: {region_ds.analysed_sst.shape}")
        print("Successfully extracted data!")
    else:
        print("No SST data found")
        
except Exception as e:
    print(f"Error in selection: {e}")
    import traceback
    traceback.print_exc()