
import xarray as xr
import numpy as np
from datetime import date, timedelta
import pandas as pd
from collections import defaultdict

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_ext.analysed_sst.values.astype(np.float64)
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

# Day of year mapping: cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

# Verify
print("Jan 1:", get_doy(date(2000,1,1)))  # should be 1
print("Feb 28:", get_doy(date(2000,2,28)))  # should be 59
print("Feb 29:", get_doy(date(2000,2,29)))  # should be 60
print("Mar 1:", get_doy(date(2000,3,1)))  # should be 61
print("Dec 31:", get_doy(date(2000,12,31)))  # should be 366

# Baseline dates only (1992-01-01 to 2002-12-31)
baseline_mask = np.array([(date(1992,1,1) <= d <= date(2002,12,31)) for d in baseline_dates])
baseline_idx = np.where(baseline_mask)[0]
print("Number of baseline dates:", len(baseline_idx))

# Build pools: pool_indices[doy] = list of date indices into baseline_sst
pool_indices = defaultdict(list)

for bi in baseline_idx:
    b = baseline_dates[bi]
    b_doy = get_doy(b)
    if b_doy == 60:
        continue  # day 60 gets no pool of its own
    lo = max(0, bi - 5)
    hi = min(len(baseline_dates)-1, bi + 5)
    indices = list(range(lo, hi+1))
    pool_indices[b_doy].extend(indices)

# Check pools
print("Number of day-of-year pools:", len(pool_indices))
for d in [1, 59, 60, 61, 90, 180, 365, 366]:
    n = len(pool_indices.get(d, []))
    print(f"Pool {d}: {n} dates")
