import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")

# Region bounds
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

# Subset region
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Time ranges
# Baseline: 1992-01-01 to 2002-12-31. 
# To accommodate +/- 5 days, we need from 1991-12-27 to 2003-01-05.
baseline_start = '1991-12-27'
baseline_end = '2003-01-05'
target_start = '2010-06-01'
target_end = '2010-08-31'

# We'll load the baseline and target separately or combined. 
# Given the memory, let's see how large the region is.
print(f"Region shape: {ds_reg.analysed_sst.shape[1:]}")
# Region shape: (lat_len, lon_len)
# Total time points: (2003-1991)*365.25 + (2010-2003)*365.25 ... 
# Actually, let's just slice the dataset.

# Extract baseline data
ds_baseline = ds_reg.sel(time=slice(baseline_start, baseline_end)).load()
# Extract target data
ds_target = ds_reg.sel(time=slice(target_start, target_end)).load()

print(f"Baseline shape: {ds_baseline.analysed_sst.shape}")
print(f"Target shape: {ds_target.analysed_sst.shape}")
