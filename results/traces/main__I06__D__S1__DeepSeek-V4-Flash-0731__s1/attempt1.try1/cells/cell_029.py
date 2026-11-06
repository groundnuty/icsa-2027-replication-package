
import numpy as np
import datetime
import pandas as pd

# Rebuild pools to verify
baseline_sst = np.load('/work/baseline_sst.npy')
baseline_time_idx = np.load('/work/baseline_time_idx.npy')

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values
baseline_dates = time[baseline_time_idx]
baseline_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in baseline_dates]

def doy_from_date(date):
    m = date.month
    d = date.day
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    elif m == 3:
        return 60 + d
    elif m == 4:
        return 91 + d
    elif m == 5:
        return 121 + d
    elif m == 6:
        return 152 + d
    elif m == 7:
        return 182 + d
    elif m == 8:
        return 213 + d
    elif m == 9:
        return 244 + d
    elif m == 10:
        return 274 + d
    elif m == 11:
        return 305 + d
    elif m == 12:
        return 335 + d
    return -1

date_to_idx = {}
for i, d in enumerate(baseline_dates_list):
    date_to_idx[d] = i

core_dates = [d for d in baseline_dates_list 
              if datetime.date(1992,1,1) <= d <= datetime.date(2002,12,31)]
core_doy = {d: doy_from_date(d) for d in core_dates}

# Verify some pools
pools = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    matching_dates = [d for d, dd in core_doy.items() if dd == doy]
    pool_dates = set()
    for t0 in matching_dates:
        for delta in range(-5, 6):
            t = t0 + datetime.timedelta(days=delta)
            if t in date_to_idx:
                pool_dates.add(t)
    pools[doy] = sorted(pool_dates)

# Verify pool sizes
for doy in [1, 59, 60, 61, 153, 213, 365, 366]:
    if doy in pools:
        print(f"Day {doy}: {len(pools[doy])} dates")
        # Check if all have data
        idxs = [date_to_idx[d] for d in pools[doy]]
        # Verify these indices have data
        sst_vals = baseline_sst[idxs, :, :]
        print(f"  SST shape: {sst_vals.shape}")
        print(f"  NaN in first cell: {np.isnan(sst_vals[:, 0, 0]).sum()}")
    else:
        print(f"Day {doy}: no pool (day 60)")

# Check specific pool contents for day 153 (June 1)
print(f"\nDay 153 pool dates:")
print(f"  First: {pools[153][0]}, Last: {pools[153][-1]}")
print(f"  Count: {len(pools[153])}")

# Check if all baseline years are represented
for y in range(1992, 2003):
    year_dates = [d for d in pools[153] if d.year == y]
    print(f"  {y}: {len(year_dates)} dates")
