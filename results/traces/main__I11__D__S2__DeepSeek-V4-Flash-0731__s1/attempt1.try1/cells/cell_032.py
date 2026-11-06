
import numpy as np
from datetime import date, timedelta
import pandas as pd
from collections import defaultdict
import xarray as xr

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))
baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

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

baseline_dates_list = list(baseline_dates)

pool1 = pool_indices.get(1, [])
print(f"Pool 1 has {len(pool1)} dates")
for d in [date(1991,12,27), date(1991,12,31), date(1992,1,1), date(1992,1,6)]:
    try:
        idx = baseline_dates_list.index(d)
        if idx in pool1:
            print(f"  {d} is in pool 1")
        else:
            print(f"  {d} is NOT in pool 1")
    except ValueError:
        print(f"  {d} not in dataset")

# Check pool 60: should be empty
pool60 = pool_indices.get(60, [])
print(f"\nPool 60 has {len(pool60)} dates")

# Check if Feb 29 dates appear in pools of neighboring days
# Feb 29 2000 should be in pool 59 (Feb 28) and pool 61 (Mar 1)
feb29_2000 = date(2000,2,29)
idx = baseline_dates_list.index(feb29_2000)
print(f"\nFeb 29 2000 (index {idx}) is in pools:")
for d in sorted(pool_indices.keys()):
    if idx in pool_indices[d]:
        print(f"  Pool {d}")
