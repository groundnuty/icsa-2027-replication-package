
import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Load baseline data for the region
baseline_idx = np.arange(3647, 7675)  # 4028 points
target_idx = np.arange(14396, 14488)  # 92 points

# Use isel to load only the needed data
print("Loading baseline data...")
baseline_ds = ds.isel(time=baseline_idx, latitude=slice(109, 169), longitude=slice(373, 433))
baseline_sst = baseline_ds['analysed_sst'].load()
print(f"Baseline shape: {baseline_sst.shape}")
print(f"Baseline time: {baseline_ds.time.values[0]} to {baseline_ds.time.values[-1]}")
print(f"Baseline memory: {baseline_sst.nbytes / 1e6:.1f} MB")

print("\nLoading target data...")
target_ds = ds.isel(time=target_idx, latitude=slice(109, 169), longitude=slice(373, 433))
target_sst = target_ds['analysed_sst'].load()
print(f"Target shape: {target_sst.shape}")
print(f"Target time: {target_ds.time.values[0]} to {target_ds.time.values[-1]}")
