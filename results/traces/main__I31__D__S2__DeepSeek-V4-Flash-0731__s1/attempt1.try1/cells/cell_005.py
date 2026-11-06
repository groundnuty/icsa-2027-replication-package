
import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

time = ds.time.values
print("First:", time[0])
print("Last:", time[-1])

# Find baseline period indices: 1992-01-01 to 2002-12-31
import datetime
base_start = np.datetime64('1992-01-01')
base_end = np.datetime64('2002-12-31')
base_mask = (time >= base_start) & (time <= base_end)
base_idx = np.where(base_mask)[0]
print("Baseline indices:", base_idx[0], "to", base_idx[-1])
print("Baseline dates:", time[base_idx[0]], "to", time[base_idx[-1]])

# Find target period indices: 2017-06-01 to 2017-08-31
target_start = np.datetime64('2017-06-01')
target_end = np.datetime64('2017-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_idx = np.where(target_mask)[0]
print("Target indices:", target_idx[0], "to", target_idx[-1])
print("Target dates:", time[target_idx[0]], "to", time[target_idx[-1]])
print("Number of target days:", len(target_idx))

# Also need the days just outside baseline for window purposes
# Windows extend 5 days before 1992-01-01 and 5 days after 2002-12-31
ext_start = np.datetime64('1991-12-27')
ext_end = np.datetime64('2003-01-05')
ext_mask = (time >= ext_start) & (time <= ext_end)
ext_idx = np.where(ext_mask)[0]
print("Extended baseline indices:", ext_idx[0], "to", ext_idx[-1])
print("Extended dates:", time[ext_idx[0]], "to", time[ext_idx[-1]])
