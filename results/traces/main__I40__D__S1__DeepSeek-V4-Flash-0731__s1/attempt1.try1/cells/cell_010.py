
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Get time values
times = ds.time.values

# Find indices for our time periods
# Baseline: 1992-01-01 to 2002-12-31, plus window extension
# 1991-12-27 to 2003-01-05
# Target: 2009-06-01 to 2009-08-31

from datetime import datetime

# Baseline period with window extension
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
target_start = np.datetime64('2009-06-01')
target_end = np.datetime64('2009-08-31')

base_idx = np.where((times >= baseline_start) & (times <= baseline_end))[0]
targ_idx = np.where((times >= target_start) & (times <= target_end))[0]

print(f"Baseline indices: {len(base_idx)}, first: {times[base_idx[0]]}, last: {times[base_idx[-1]]}")
print(f"Target indices: {len(targ_idx)}, first: {times[targ_idx[0]]}, last: {times[targ_idx[-1]]}")

# Check that all expected days are present
import pandas as pd
base_dates = pd.date_range('1991-12-27', '2003-01-05', freq='D')
actual_base = pd.DatetimeIndex(times[base_idx])
print(f"Expected baseline days: {len(base_dates)}")
print(f"Actual baseline days: {len(actual_base)}")
print(f"Missing: {len(base_dates.difference(actual_base))}")
if len(base_dates.difference(actual_base)) > 0:
    print(base_dates.difference(actual_base))

targ_dates = pd.date_range('2009-06-01', '2009-08-31', freq='D')
actual_targ = pd.DatetimeIndex(times[targ_idx])
print(f"Expected target days: {len(targ_dates)}")
print(f"Actual target days: {len(actual_targ)}")
print(f"Missing: {len(targ_dates.difference(actual_targ))}")
if len(targ_dates.difference(actual_targ)) > 0:
    print(targ_dates.difference(actual_targ))
