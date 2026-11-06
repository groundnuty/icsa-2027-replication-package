
import xarray as xr
import numpy as np
import pandas as pd

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# Region indices
lat_idx = np.arange(217, 277)  # 57.84 to 59.02
lon_idx = np.arange(421, 481)  # 17.42 to 18.60

# Baseline window: 1991-12-27 to 2003-01-05
base_start_idx = 3647
base_end_idx = 7674
# Target: 2007-06-01 to 2007-08-31
tgt_start_idx = 9282
tgt_end_idx = 9373

# Extract baseline data
print("Loading baseline data...")
base_data = ds.analysed_sst.values[base_start_idx:base_end_idx+1, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
print(f"Baseline shape: {base_data.shape}")
print(f"Baseline dtype: {base_data.dtype}")
print(f"NaN count in baseline: {np.isnan(base_data).sum()}")

# Extract target data
print("Loading target data...")
tgt_data = ds.analysed_sst.values[tgt_start_idx:tgt_end_idx+1, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
print(f"Target shape: {tgt_data.shape}")
print(f"Target dtype: {tgt_data.dtype}")
print(f"NaN count in target: {np.isnan(tgt_data).sum()}")
