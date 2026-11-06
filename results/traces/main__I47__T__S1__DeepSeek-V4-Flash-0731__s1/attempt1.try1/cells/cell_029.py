
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

base_times = np.load('/tmp/base_times.npy')
base_dt = [pd.Timestamp(t).to_pydatetime() for t in base_times]

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

baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

doy_to_baseline_dates = defaultdict(list)
d = baseline_start
while d <= baseline_end:
    doy = date_to_doy(d)
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

date_to_idx = {}
for i, dt in enumerate(base_dt):
    date_to_idx[dt] = i

# Check which dates are used in any pool
used_dates = set()
for d in range(1, 367):
    if d == 60:
        continue
    for Y in doy_to_baseline_dates.get(d, []):
        for i in range(-5, 6):
            X = Y + timedelta(days=i)
            if X in date_to_idx:
                used_dates.add(X)

used_dates_sorted = sorted(used_dates)
print(f"Number of unique dates used: {len(used_dates_sorted)}")
print(f"First date used: {used_dates_sorted[0]}")
print(f"Last date used: {used_dates_sorted[-1]}")

# Check if all dates from 1991-12-27 to 2003-01-05 are used
all_dates_in_range = set()
d = datetime(1991, 12, 27)
while d <= datetime(2003, 1, 5):
    all_dates_in_range.add(d)
    d += timedelta(days=1)

print(f"All dates in range 1991-12-27 to 2003-01-05: {len(all_dates_in_range)}")
print(f"Dates used that are in the range: {len(used_dates.intersection(all_dates_in_range))}")
print(f"Dates in range but NOT used: {len(all_dates_in_range - used_dates)}")
missing = sorted(all_dates_in_range - used_dates)
if missing:
    print(f"Missing dates (first 10): {missing[:10]}")
    print(f"Missing dates (last 10): {missing[-10:]}")
