
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')

f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

times = ds.time.values
print("First:", times[0])
print("Last:", times[-1])
print("Count:", len(times))

# Find indices for baseline: 1992-01-01 to 2002-12-31, plus window padding
# and target: 2007-06-01 to 2007-08-31

import datetime as dt

# Find time indices for baseline period
base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
base_idx = np.where((times >= base_start) & (times <= base_end))[0]
print("Baseline indices:", base_idx[0], base_idx[-1], "count:", len(base_idx))
print("Baseline dates:", times[base_idx[0]], "to", times[base_idx[-1]])

# Target period
target_start = np.datetime64('2007-06-01')
target_end = np.datetime64('2007-08-31')
target_idx = np.where((times >= target_start) & (times <= target_end))[0]
print("Target indices:", target_idx[0], target_idx[-1], "count:", len(target_idx))
print("Target dates:", times[target_idx[0]], "to", times[target_idx[-1]])
