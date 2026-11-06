import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
times = ds.time.values

# Convert to datetime
from datetime import datetime, timedelta

# Find indices for baseline period with windows
# 1991-12-27 to 2003-01-05
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')

# Target: 2007-06-01 to 2007-08-31
target_start = np.datetime64('2007-06-01')
target_end = np.datetime64('2007-08-31')

baseline_mask = (times >= baseline_start) & (times <= baseline_end)
target_mask = (times >= target_start) & (times <= target_end)

print("Baseline indices:", np.where(baseline_mask)[0][0], "to", np.where(baseline_mask)[0][-1])
print("Target indices:", np.where(target_mask)[0][0], "to", np.where(target_mask)[0][-1])
print("Baseline days:", np.sum(baseline_mask))
print("Target days:", np.sum(target_mask))

# Let's also check the actual dates at these indices
base_idx = np.where(baseline_mask)[0]
targ_idx = np.where(target_mask)[0]
print("Baseline first date:", times[base_idx[0]])
print("Baseline last date:", times[base_idx[-1]])
print("Target first date:", times[targ_idx[0]])
print("Target last date:", times[targ_idx[-1]])
