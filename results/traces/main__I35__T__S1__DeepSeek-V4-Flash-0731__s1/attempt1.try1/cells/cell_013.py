
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')

f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

times = ds.time.values
print(f"Total times: {len(times)}")
print(f"First: {times[0]}")
print(f"Last: {times[-1]}")

# Find indices for our needed periods
# Baseline: 1991-12-27 to 2003-01-05 (with extension)
# Target: 2009-06-01 to 2009-08-31

import datetime

# Convert to datetime
dt_times = np.array([np.datetime64(t) for t in times])

# Baseline range (with windows)
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
bl_mask = (dt_times >= baseline_start) & (dt_times <= baseline_end)
bl_idx = np.where(bl_mask)[0]
print(f"Baseline period: {len(bl_idx)} days, from {dt_times[bl_idx[0]]} to {dt_times[bl_idx[-1]]}")

# Target range
target_start = np.datetime64('2009-06-01')
target_end = np.datetime64('2009-08-31')
tg_mask = (dt_times >= target_start) & (dt_times <= target_end)
tg_idx = np.where(tg_mask)[0]
print(f"Target period: {len(tg_idx)} days, from {dt_times[tg_idx[0]]} to {dt_times[tg_idx[-1]]}")
