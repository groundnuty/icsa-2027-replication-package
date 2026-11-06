
import fsspec
import xarray as xr
import numpy as np
import datetime

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Find time indices for baseline and target
time_vals = ds.time.values
print("First time:", time_vals[0])
print("Last time:", time_vals[-1])

# Baseline: 1991-12-27 to 2003-01-05
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (ds.time.values >= baseline_start) & (ds.time.values <= baseline_end)
baseline_indices = np.where(baseline_mask)[0]
print(f"Baseline indices: {baseline_indices[0]} to {baseline_indices[-1]}, count={len(baseline_indices)}")

# Target: 2014-06-01 to 2014-08-31
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')
target_mask = (ds.time.values >= target_start) & (ds.time.values <= target_end)
target_indices = np.where(target_mask)[0]
print(f"Target indices: {target_indices[0]} to {target_indices[-1]}, count={len(target_indices)}")
