
import xarray as xr
import numpy as np
import datetime as dt

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Define region indices
lat_min_idx, lat_max_idx = 34, 93  # inclusive
lon_min_idx, lon_max_idx = 213, 272  # inclusive

# Baseline period: 1991-12-27 to 2003-01-05 (baseline years 1992-2002 plus window)
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')

# Target period
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')

# Select data for the region
sst_region = ds['analysed_sst'][:, lat_min_idx:lat_max_idx+1, lon_min_idx:lon_max_idx+1]
print(f"Region shape: {sst_region.shape}")

# Get time indices for baseline and target
times = ds.time.values
baseline_mask = (times >= baseline_start) & (times <= baseline_end)
target_mask = (times >= target_start) & (times <= target_end)

print(f"Baseline time indices: {np.where(baseline_mask)[0][0]} to {np.where(baseline_mask)[0][-1]}")
print(f"Target time indices: {np.where(target_mask)[0][0]} to {np.where(target_mask)[0][-1]}")
print(f"Baseline days: {np.sum(baseline_mask)}")
print(f"Target days: {np.sum(target_mask)}")

# Load baseline and target data
baseline_data = sst_region.values[baseline_mask]  # shape: (n_baseline_days, 60, 60)
target_data = sst_region.values[target_mask]  # shape: (n_target_days, 60, 60)
baseline_times = times[baseline_mask]
target_times = times[target_mask]

print(f"Baseline data shape: {baseline_data.shape}")
print(f"Target data shape: {target_data.shape}")
print(f"Baseline times: {baseline_times[0]} to {baseline_times[-1]}")
print(f"Target times: {target_times[0]} to {target_times[-1]}")
