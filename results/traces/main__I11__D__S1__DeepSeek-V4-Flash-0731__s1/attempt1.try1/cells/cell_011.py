
import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

time = ds.time.values

# Baseline period: 1991-12-27 to 2003-01-05 (with windows)
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')

# Target: 2021-06-01 to 2021-08-31
target_start = np.datetime64('2021-06-01')
target_end = np.datetime64('2021-08-31')

baseline_mask = (time >= baseline_start) & (time <= baseline_end)
target_mask = (time >= target_start) & (time <= target_end)

baseline_idx = np.where(baseline_mask)[0]
target_idx = np.where(target_mask)[0]

print(f"Baseline indices: {baseline_idx[0]} to {baseline_idx[-1]}, count: {len(baseline_idx)}")
print(f"Target indices: {target_idx[0]} to {target_idx[-1]}, count: {len(target_idx)}")
print(f"Baseline dates: {time[baseline_idx[0]]} to {time[baseline_idx[-1]]}")
print(f"Target dates: {time[target_idx[0]]} to {time[target_idx[-1]]}")

# Region indices
lat_idx = np.arange(109, 169)
lon_idx = np.arange(373, 433)
print(f"lat_idx: {lat_idx}")
print(f"lon_idx: {lon_idx}")
