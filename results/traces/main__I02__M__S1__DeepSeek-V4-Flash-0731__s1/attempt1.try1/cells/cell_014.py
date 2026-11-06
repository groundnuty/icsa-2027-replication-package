
import numpy as np
from datetime import date, timedelta

# All dates from 1991-12-27 to 2003-01-05
full_start = date(1991, 12, 27)
full_end = date(2003, 1, 5)
full_dates = []
d = full_start
while d <= full_end:
    full_dates.append(d)
    d += timedelta(days=1)

# Map each date to its index in the full list
date_to_idx = {d: i for i, d in enumerate(full_dates)}
print(f"Full date range: {len(full_dates)} dates from {full_start} to {full_end}")

# For each DOY, find the indices of dates in its pool
def doy_from_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month - 1] + d.day

# Baseline dates 1992-01-01 to 2002-12-31
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# For each DOY, build list of baseline dates with that doy
doy_to_baseline_dates = {}
d = baseline_start
while d <= baseline_end:
    doy = doy_from_date(d)
    if doy not in doy_to_baseline_dates:
        doy_to_baseline_dates[doy] = []
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

# For each DOY (except 60), build the pool of date indices
doy_to_pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for bd in doy_to_baseline_dates[doy]:
        for offset in range(-5, 6):
            d = bd + timedelta(days=offset)
            if d in date_to_idx:
                pool_dates.add(date_to_idx[d])
    doy_to_pool_indices[doy] = sorted(pool_dates)

# Verify some pools
for doy in [1, 59, 61, 100, 366]:
    idx = doy_to_pool_indices[doy]
    dates = [full_dates[i] for i in idx]
    print(f"DOY {doy}: {len(idx)} dates, {dates[0]} to {dates[-1]}")
    if doy == 59:
        # Check if Feb 29 dates are in the pool for DOY 59
        feb29_dates = [d for d in dates if d.month == 2 and d.day == 29]
        print(f"  Feb 29 dates in DOY 59 pool: {feb29_dates}")
