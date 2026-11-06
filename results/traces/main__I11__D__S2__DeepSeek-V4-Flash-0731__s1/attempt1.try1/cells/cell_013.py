
import numpy as np
from datetime import date, timedelta
from collections import defaultdict

# We'll reuse the loaded data. Let me re-run the full loading in one script.
# Actually let me continue from where we are - need to reload since this is a new cell.

import xarray as xr
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_ext.analysed_sst.values.astype(np.float64)
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

# Sea cells
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", sea_mask.sum())

# Day of year
CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

# Build pools
baseline_mask = np.array([(date(1992,1,1) <= d <= date(2002,12,31)) for d in baseline_dates])
baseline_idx = np.where(baseline_mask)[0]

pool_indices = defaultdict(list)
for bi in baseline_idx:
    b = baseline_dates[bi]
    b_doy = get_doy(b)
    if b_doy == 60:
        continue
    lo = max(0, bi - 5)
    hi = min(len(baseline_dates)-1, bi + 5)
    pool_indices[b_doy].extend(list(range(lo, hi+1)))

# For each pool, gather unique indices (some may appear multiple times)
# Actually, should we keep duplicates? The pool is "every SST value whose date lies within ±5 days".
# If a date falls within ±5 days of multiple baseline dates with the same day-of-year, 
# it should be counted multiple times? Or once?
# The method says "the pool is every SST value whose date lies within ±5 calendar days of a baseline date whose day of year is d."
# I think each value is included once per baseline date it's within ±5 days of. But actually, 
# if the same date is within 5 days of two different baseline dates with the same day-of-year 
# (e.g., Feb 28 1992 and Feb 28 1993), then that date appears multiple times in the pool.
# Hmm, but actually a single date can be within 5 days of a baseline date in a specific year.
# For example, Feb 25 1993 is within 5 days of Feb 28 1993 (doy 59) but also within 5 days of 
# Mar 1 1993 (doy 61). So Feb 25 1993 appears in pools for both doy 59 and doy 61.
# But within a single pool (e.g., doy 59), Feb 25 1993 appears once per baseline date of doy 59 
# that it's within 5 days of. Feb 25 1993 is within 5 days of Feb 28 1993 (baseline, doy 59), 
# and possibly also Feb 28 1992 (if |Feb 25 1993 - Feb 28 1992| <= 5? No, that's ~1 year apart).
# So each date appears at most once per pool.
# So duplicates might not occur, but let me check.

# Let me check for duplicates in pool 59
pool59 = pool_indices[59]
print("Pool 59 indices:", len(pool59), "unique:", len(set(pool59)))
