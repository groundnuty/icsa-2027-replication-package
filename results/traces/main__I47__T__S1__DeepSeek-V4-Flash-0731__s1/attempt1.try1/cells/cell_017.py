
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

# Load saved data
base_data = np.load('/tmp/base_data.npy')
tgt_data = np.load('/tmp/tgt_data.npy')
base_times = np.load('/tmp/base_times.npy')
tgt_times = np.load('/tmp/tgt_times.npy')

def day_of_year(month, day):
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and day == 29:
        return 60
    doy = sum(days_in_month[:month-1]) + day
    if month > 2:
        doy += 1
    return doy

def date_to_doy(dt):
    return day_of_year(dt.month, dt.day)

# Convert base times to Python datetimes
base_dt = [pd.Timestamp(t).to_pydatetime() for t in base_times]

# Build baseline dates (1992-01-01 to 2002-12-31) with their day-of-year
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Group baseline dates by day-of-year
doy_to_baseline_dates = defaultdict(list)
d = baseline_start
while d <= baseline_end:
    doy = date_to_doy(d)
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

# For each doy d (excluding 60), find which indices in base_data belong to pool d
# For each doy, pool dates = all dates X within ±5 days of any baseline date Y with doy(Y)=d
# base_data covers 1991-12-27 to 2003-01-05

# First, let's map each base date to its index
date_to_idx = {}
for i, dt in enumerate(base_dt):
    date_to_idx[dt] = i

print(f"Total base dates: {len(base_dt)}")
print(f"Date to index mapping size: {len(date_to_idx)}")

# Now for each doy d (1-59, 61-366), find pool indices
doy_to_pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    indices = set()
    for Y in doy_to_baseline_dates.get(d, []):
        for i in range(-5, 6):
            X = Y + timedelta(days=i)
            if X in date_to_idx:
                indices.add(date_to_idx[X])
    doy_to_pool_indices[d] = sorted(indices)
    if d in [1, 59, 61, 153, 244, 366]:
        print(f"DOY {d}: {len(indices)} pool dates, first few indices: {sorted(indices)[:3]}, last few: {sorted(indices)[-3:]}")

# Check total
total = sum(len(v) for v in doy_to_pool_indices.values())
print(f"Total pool entries across all doy: {total}")
print(f"Number of doy with pools: {len(doy_to_pool_indices)}")
