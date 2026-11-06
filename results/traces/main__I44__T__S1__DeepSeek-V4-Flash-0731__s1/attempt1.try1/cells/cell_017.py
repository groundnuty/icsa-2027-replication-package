import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd
from collections import defaultdict

# Load data
base_ds = xr.open_dataset('/tmp/base_data.nc')
target_ds = xr.open_dataset('/tmp/target_data.nc')
base_sst = base_ds['analysed_sst'].values.astype(np.float64)  # (4028, 60, 60)
target_sst = target_ds['analysed_sst'].values.astype(np.float64)  # (92, 60, 60)
base_time = base_ds['time'].values
target_time = target_ds['time'].values

# Convert to dates
base_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

def day_of_year(date):
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    if not is_leap and date.month >= 3:
        doy += 1
    return doy

# Build baseline_dates_by_doy
baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)
baseline_dates_by_doy = defaultdict(list)
for date in base_dates:
    if baseline_start <= date <= baseline_end:
        d = day_of_year(date)
        baseline_dates_by_doy[d].append(date)

# Build mapping from date to index in base_dates
date_to_idx = {d: i for i, d in enumerate(base_dates)}

# For each day-of-year d (1-366, d≠60), find the pool indices
pool_indices = defaultdict(set)

for d, dates in baseline_dates_by_doy.items():
    if d == 60:
        continue
    for b in dates:
        for delta in range(-5, 6):
            t = b + dt.timedelta(days=delta)
            if t in date_to_idx:
                pool_indices[d].add(date_to_idx[t])

print("Pool sizes for some DOYs:")
for d in [1, 59, 61, 366]:
    print(f"  DOY {d}: {len(pool_indices[d])} dates")

# Check
missing = set(range(1, 367)) - set(pool_indices.keys()) - {60}
print("Missing pool DOYs:", missing)
print("Pool DOYs count:", len(pool_indices))

# For day 60, pool is empty (no pool of its own)
# Threshold and climatology for day 60 = mean of days 59 and 61
