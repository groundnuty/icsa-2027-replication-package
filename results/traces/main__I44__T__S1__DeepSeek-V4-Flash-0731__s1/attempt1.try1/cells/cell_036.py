import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd
from collections import defaultdict

# Load data
base_ds = xr.open_dataset('/tmp/base_data.nc')
base_time = base_ds['time'].values
base_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]

def day_of_year(date):
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    if not is_leap and date.month >= 3:
        doy += 1
    return doy

baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)
baseline_dates_by_doy = defaultdict(list)
for date in base_dates:
    if baseline_start <= date <= baseline_end:
        d = day_of_year(date)
        baseline_dates_by_doy[d].append(date)

date_to_idx = {d: i for i, d in enumerate(base_dates)}

pool_indices = defaultdict(set)
for d, dates in baseline_dates_by_doy.items():
    if d == 60:
        continue
    for b in dates:
        for delta in range(-5, 6):
            t = b + dt.timedelta(days=delta)
            if t in date_to_idx:
                pool_indices[d].add(date_to_idx[t])

# Check pool sizes
print("Pool sizes for various DOYs:")
for d in [1, 31, 59, 61, 90, 153, 244, 366]:
    dates_in_pool = sorted([base_dates[i] for i in pool_indices[d]])
    print(f"  DOY {d}: {len(pool_indices[d])} dates")
    if d in [1, 59, 61, 366]:
        print(f"    First: {dates_in_pool[0]}, Last: {dates_in_pool[-1]}")
        # Check which years are represented
        years = set(d.year for d in dates_in_pool)
        print(f"    Years: {sorted(years)}")

# For DOY 59, check that Feb 29 from leap years are included
doy59_dates = sorted([base_dates[i] for i in pool_indices[59]])
feb29_dates = [d for d in doy59_dates if d.month == 2 and d.day == 29]
print(f"\nDOY 59: Feb 29 dates in pool: {feb29_dates}")

# For DOY 61, check Feb 29 dates
doy61_dates = sorted([base_dates[i] for i in pool_indices[61]])
feb29_dates_61 = [d for d in doy61_dates if d.month == 2 and d.day == 29]
print(f"DOY 61: Feb 29 dates in pool: {feb29_dates_61}")
