
import numpy as np
import pandas as pd
import xarray as xr

# Reload
mhw_mask = np.load('/work/mhw_mask.npy')
sea_mask = np.load('/work/sea_mask.npy')

# Active days
active = mhw_mask.any(axis=(0, 1))
print("Active days:", active.sum())

# Find maximal runs
runs = []
t = 0
n_time = len(active)
while t < n_time:
    if active[t]:
        start = t
        while t < n_time and active[t]:
            t += 1
        end = t - 1
        runs.append((start, end))
    else:
        t += 1

print("Regional events (start_idx, end_idx):", runs)

# Get dates
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))
target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_dates = pd.to_datetime(target.time.values).date

for start, end in runs:
    print(f"Event: {target_dates[start]} to {target_dates[end]}")
