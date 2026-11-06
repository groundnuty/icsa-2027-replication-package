import xarray as xr
import numpy as np
from datetime import datetime
import os

# Open the dataset
local_path = '/work/sst_s2.nc'
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define the baseline period
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Get all data for baseline period
baseline_ds = ds.sel(time=slice(baseline_start, baseline_end))

print("Baseline period dimensions:")
print(f"  Time: {baseline_ds.time.min().values} to {baseline_ds.time.max().values}")
print(f"  Shape: {baseline_ds['analysed_sst'].shape}")

# Check if we have sufficient data for all days in baseline
print(f"\nTotal days in baseline: {len(baseline_ds.time)}")
print(f"Expected days: {(baseline_end - baseline_start).days + 1}")

# Get the region of interest for baseline too
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

baseline_region_ds = baseline_ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
print(f"\nBaseline region shape: {baseline_region_ds['analysed_sst'].shape}")

# Close datasets
ds.close()
baseline_ds.close()
baseline_region_ds.close()