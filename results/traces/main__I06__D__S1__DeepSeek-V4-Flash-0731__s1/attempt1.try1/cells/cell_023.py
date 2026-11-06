
import numpy as np
import datetime
import pandas as pd

# Load the data
baseline_sst = np.load('/work/baseline_sst.npy')  # (4028, 60, 60)
baseline_time_idx = np.load('/work/baseline_time_idx.npy')

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values
baseline_dates = time[baseline_time_idx]

# Convert to datetime.date objects
baseline_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in baseline_dates]
print(f"First 10 baseline dates: {baseline_dates_list[:10]}")
print(f"Last 10 baseline dates: {baseline_dates_list[-10:]}")

# Day of year function
def doy_from_date(date):
    y = date.year
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

# Find day 60 dates
for d in baseline_dates_list:
    if doy_from_date(d) == 60:
        print(f"Day 60: {d}")

# Find baseline dates (1992-01-01 to 2002-12-31)
baseline_core_start = datetime.date(1992, 1, 1)
baseline_core_end = datetime.date(2002, 12, 31)
core_dates = [d for d in baseline_dates_list if baseline_core_start <= d <= baseline_core_end]
print(f"\nCore baseline dates: {len(core_dates)}")
print(f"First: {core_dates[0]}, Last: {core_dates[-1]}")

# Build mapping from date to index
date_to_idx = {}
for i, d in enumerate(baseline_dates_list):
    date_to_idx[d] = i

# Day of year for core dates
core_doy = {d: doy_from_date(d) for d in core_dates}

# Build pool date lists for each day-of-year
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

# Check some pools
for doy in [1, 59, 61, 366, 153, 213]:
    dates = pools.get(doy, [])
    print(f"\nDay of year {doy}: {len(dates)} dates")
    if dates:
        print(f"  Range: {dates[0]} to {dates[-1]}")

print(f"\nDay 60 in pools: {60 in pools}")

# Check Feb 29
feb29_1992 = datetime.date(1992, 2, 29)
print(f"Feb 29 1992 in day 59 pool: {feb29_1992 in pools[59]}")
print(f"Feb 29 1992 in day 61 pool: {feb29_1992 in pools[61]}")

# Check that all window days are used
window_days = []
for d in baseline_dates_list:
    if d < datetime.date(1992,1,1) or d > datetime.date(2002,12,31):
        window_days.append(d)
print(f"\nWindow days (outside 1992-2002): {window_days}")
for wd in window_days:
    in_pools = [doy for doy, dates in pools.items() if wd in dates]
    print(f"  {wd} in pools: {in_pools}")
