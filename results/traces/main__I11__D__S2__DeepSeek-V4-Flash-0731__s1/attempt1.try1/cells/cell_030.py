
import numpy as np
from datetime import date, timedelta
import pandas as pd
from collections import defaultdict
import xarray as xr

# Load baseline data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))
baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

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

# Check pool 366 (Dec 31)
pool366 = pool_indices.get(366, [])
print(f"Pool 366 has {len(pool366)} dates")
# Check if 2003-01-01 to 2003-01-05 are in pool 366
for d in [date(2003,1,1), date(2003,1,5), date(2003,1,6)]:
    idx = baseline_dates.index(d)
    if idx in pool366:
        print(f"  {d} is in pool 366")
    else:
        print(f"  {d} is NOT in pool 366")

# Check pool 1 (Jan 1)
pool1 = pool_indices.get(1, [])
print(f"\nPool 1 has {len(pool1)} dates")
for d in [date(1991,12,27), date(1991,12,31), date(1992,1,1), date(1992,1,6)]:
    idx = baseline_dates.index(d)
    if idx in pool1:
        print(f"  {d} is in pool 1")
    else:
        print(f"  {d} is NOT in pool 1")
