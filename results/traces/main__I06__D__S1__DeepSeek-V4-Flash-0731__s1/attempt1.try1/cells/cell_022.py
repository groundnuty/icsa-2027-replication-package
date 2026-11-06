
import numpy as np
import datetime

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

# Verify day 60 exists only in leap years
for d in baseline_dates_list:
    if doy_from_date(d) == 60:
        print(f"Day 60: {d}")

# Find baseline dates (1992-01-01 to 2002-12-31) - these are the ones whose day-of-year defines the pools
# The full loaded range is 1991-12-27 to 2003-01-05
baseline_core_start = datetime.date(1992, 1, 1)
baseline_core_end = datetime.date(2002, 12, 31)

core_dates = [d for d in baseline_dates_list if baseline_core_start <= d <= baseline_core_end]
print(f"\nCore baseline dates: {len(core_dates)}")
print(f"First: {core_dates[0]}, Last: {core_dates[-1]}")

# Build a mapping from date to index in baseline_sst
date_to_idx = {}
for i, d in enumerate(baseline_dates_list):
    date_to_idx[d] = i

# For each day-of-year d (1-366, d != 60), collect all dates that contribute to its pool
import pandas as pd

# For each core baseline date, compute its day-of-year
core_doy = {d: doy_from_date(d) for d in core_dates}

# Build pool date lists for each day-of-year
pools = {}  # doy -> list of dates

# Also need: for each date in the full range, which day-of-year pools does it contribute to?
# But let's build pools by day-of-year

for doy in range(1, 367):
    if doy == 60:
        continue
    # Find all core baseline dates with this day-of-year
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
    print(f"  Range: {dates[0]} to {dates[-1]}")
    
# Check day 60 pool doesn't exist
print(f"\nDay 60 in pools: {60 in pools}")

# Check that Feb 29 values are in pools of days 59 and 61
feb29_1992 = datetime.date(1992, 2, 29)
print(f"\nFeb 29 1992 in day 59 pool: {feb29_1992 in pools[59]}")
print(f"Feb 29 1992 in day 61 pool: {feb29_1992 in pools[61]}")
print(f"Feb 29 1992 in day 60 pool: {60 in pools and feb29_1992 in pools[60]}")
