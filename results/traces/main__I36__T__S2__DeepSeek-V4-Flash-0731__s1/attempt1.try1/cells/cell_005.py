
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Time range
print("First time:", ds.time.values[0])
print("Last time:", ds.time.values[-1])

# Find indices for baseline and target
times = ds.time.values

# Target: 2003-06-01 to 2003-08-31
target_start = np.datetime64('2003-06-01')
target_end = np.datetime64('2003-08-31')
target_idx = np.where((times >= target_start) & (times <= target_end))[0]
print("Target indices:", target_idx[0], "to", target_idx[-1], "count:", len(target_idx))

# Baseline: 1992-01-01 to 2002-12-31
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')
baseline_idx = np.where((times >= baseline_start) & (times <= baseline_end))[0]
print("Baseline indices:", baseline_idx[0], "to", baseline_idx[-1], "count:", len(baseline_idx))

# Also need extended baseline for window: 1991-12-27 to 2003-01-05
ext_start = np.datetime64('1991-12-27')
ext_end = np.datetime64('2003-01-05')
ext_idx = np.where((times >= ext_start) & (times <= ext_end))[0]
print("Extended baseline indices:", ext_idx[0], "to", ext_idx[-1], "count:", len(ext_idx))
