
import numpy as np
from datetime import date, timedelta
import xarray as xr
import pandas as pd
from collections import defaultdict

# Verify threshold computation for a specific cell and day
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_ext.analysed_sst.values.astype(np.float64)
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

# Pick a sea cell (find first sea cell)
target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
sea_mask = np.all(np.isfinite(target_sst), axis=0)
sea_pos = np.where(sea_mask)
first_sea = (sea_pos[0][0], sea_pos[1][0])
print(f"First sea cell: ({first_sea[0]}, {first_sea[1]})")

# Verify day-of-year pool for doy 153 (Jun 1)
# Baseline dates with doy 153: Jun 1 of 1992-2002
# Pool: dates within ±5 days of Jun 1 of each year
# For each baseline year y, window is May 27 to Jun 6 of year y

# Manually compute the pool for doy 153
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

# Check pool 153
pool153 = pool_indices.get(153, [])
print(f"Pool 153 has {len(pool153)} dates")

# Check the dates in pool 153
baseline_dates_list = list(baseline_dates)
pool_dates = [baseline_dates_list[idx] for idx in pool153]
print("First few dates in pool 153:", pool_dates[:5])
print("Last few dates in pool 153:", pool_dates[-5:])

# Verify: should include May 27 - Jun 6 for each year 1992-2002
expected = set()
for year in range(1992, 2003):
    for offset in range(-5, 6):
        d = date(year, 6, 1) + timedelta(days=offset)
        expected.add(d)

actual = set(pool_dates)
print("All expected dates present:", expected == actual)
print("Any unexpected dates:", actual - expected)
