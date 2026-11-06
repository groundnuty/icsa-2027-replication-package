
from datetime import date, timedelta
import numpy as np

def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

# Baseline period
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# Build mapping from day-of-year to list of baseline dates
doy_to_baseline_dates = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy not in doy_to_baseline_dates:
        doy_to_baseline_dates[doy] = []
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

# For each doy, compute the set of dates in the pool
doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for b in doy_to_baseline_dates.get(doy, []):
        for i in range(-5, 6):
            pool_dates.add(b + timedelta(days=i))
    doy_to_pool_dates[doy] = sorted(pool_dates)

# Check sizes
for doy in [1, 59, 61, 153, 244, 366]:
    print(f"doy {doy}: {len(doy_to_pool_dates[doy])} dates, first={doy_to_pool_dates[doy][0]}, last={doy_to_pool_dates[doy][-1]}")

# Check what the min and max dates are
all_dates = set()
for doy, dates in doy_to_pool_dates.items():
    all_dates.update(dates)
print(f"Min date: {min(all_dates)}")
print(f"Max date: {max(all_dates)}")
print(f"Total unique dates: {len(all_dates)}")

# Check how many baseline dates each doy has
for doy in [1, 59, 61, 366]:
    print(f"doy {doy}: {len(doy_to_baseline_dates.get(doy, []))} baseline dates")
print(f"doy 60: {len(doy_to_baseline_dates.get(60, []))} baseline dates (should be 3 for 1992, 1996, 2000)")
