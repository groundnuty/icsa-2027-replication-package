
import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Get lat/lon indices
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= 61.57) & (lat_vals <= 62.77)
lon_mask = (lon_vals >= 20.17) & (lon_vals <= 21.37)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

times = ds.time.values

# Baseline and target
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
target_start = np.datetime64('2009-06-01')
target_end = np.datetime64('2009-08-31')

base_mask = (times >= baseline_start) & (times <= baseline_end)
targ_mask = (times >= target_start) & (times <= target_end)

base_times = times[base_mask]
targ_times = times[targ_mask]

print(f"Baseline times: {base_times[0]} to {base_times[-1]}, count={len(base_times)}")
print(f"Target times: {targ_times[0]} to {targ_times[-1]}, count={len(targ_times)}")

# Load baseline data
baseline_sst = ds.analysed_sst.isel(time=base_mask, latitude=lat_idx, longitude=lon_idx).values
target_sst = ds.analysed_sst.isel(time=targ_mask, latitude=lat_idx, longitude=lon_idx).values

print(f"Baseline shape: {baseline_sst.shape}")
print(f"Target shape: {target_sst.shape}")

# Save for later use
np.save('/work/baseline_sst.npy', baseline_sst)
np.save('/work/target_sst.npy', target_sst)
np.save('/work/base_times.npy', base_times)
np.save('/work/targ_times.npy', targ_times)
print("Saved data")

# Check for NaN in baseline
print(f"Baseline NaN count: {np.isnan(baseline_sst).sum()}")
print(f"Baseline total: {baseline_sst.size}")
print(f"Baseline NaN fraction: {np.isnan(baseline_sst).sum() / baseline_sst.size:.4f}")

# Check for NaN in target
print(f"Target NaN count: {np.isnan(target_sst).sum()}")
print(f"Target total: {target_sst.size}")
print(f"Target NaN fraction: {np.isnan(target_sst).sum() / target_sst.size:.4f}")

# Check some values
print(f"Baseline sample values (first cell, first 5 days): {baseline_sst[:5, 0, 0]}")
print(f"Target sample values (first cell, first 5 days): {target_sst[:5, 0, 0]}")
