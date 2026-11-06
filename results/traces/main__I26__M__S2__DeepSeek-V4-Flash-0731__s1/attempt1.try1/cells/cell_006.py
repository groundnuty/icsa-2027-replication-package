
import xarray as xr
import numpy as np
import pandas as pd
import os

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
print("File size:", os.path.getsize(path))

# Try to open and check the memory
import resource
print(f"Memory limit: {resource.getrlimit(resource.RLIMIT_AS)}")

# Use lazy loading with .isel and .load() on the subset
ds = xr.open_dataset(path, engine='h5netcdf')

# Region
lat_idx = slice(217, 277)  # 60 cells
lon_idx = slice(421, 481)  # 60 cells

# Baseline window
base_start_idx = 3647
base_end_idx = 7674
tgt_start_idx = 9282
tgt_end_idx = 9373

# Try loading just the baseline subset
print("Loading baseline subset...")
base_sub = ds.analysed_sst.isel(time=slice(base_start_idx, base_end_idx+1), 
                                  latitude=lat_idx, longitude=lon_idx)
print("Subset created (lazy)")
print(f"Shape: {base_sub.shape}")

# Load it
base_data = base_sub.values
print(f"Loaded baseline, shape: {base_data.shape}, dtype: {base_data.dtype}")
print(f"NaN count: {np.isnan(base_data).sum()}")
