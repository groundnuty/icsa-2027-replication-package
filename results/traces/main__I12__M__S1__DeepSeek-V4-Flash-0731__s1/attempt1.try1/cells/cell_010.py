
from datetime import date, timedelta
import os

# Find all unique dates needed for baseline
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

def day_of_year(d):
    month = d.month
    day = d.day
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month]) + day
    if month > 2:
        doy += 1
    return doy

# Collect all baseline dates by day of year
baseline_by_doy = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy not in baseline_by_doy:
        baseline_by_doy[doy] = []
    baseline_by_doy[doy].append(d)
    d += timedelta(days=1)

# For each day of year (except 60), build pool dates
all_pool_dates = set()
for doy in range(1, 367):
    if doy == 60:
        continue
    for bd in baseline_by_doy.get(doy, []):
        for i in range(-5, 6):
            all_pool_dates.add(bd + timedelta(days=i))

# Sort all dates
all_pool_dates = sorted(all_pool_dates)
print(f"Total unique pool dates: {len(all_pool_dates)}")
print(f"First: {all_pool_dates[0]}")
print(f"Last: {all_pool_dates[-1]}")

# Target dates
target_start = date(2009, 6, 1)
target_end = date(2009, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)
print(f"Target dates: {len(target_dates)}")
