import numpy as np
import pandas as pd
from datetime import date, timedelta

# Build day-of-year mapping (1-366)
def day_of_year(month, day):
    """Map month/day to day of year 1-366 using the specified scheme."""
    # Days in each month
    # Jan: 31, Feb: 29, Mar: 31, Apr: 30, May: 31, Jun: 30,
    # Jul: 31, Aug: 31, Sep: 30, Oct: 31, Nov: 30, Dec: 31
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = day
    for m in range(month - 1):
        doy += month_days[m]
    return doy

# Test
assert day_of_year(1, 1) == 1
assert day_of_year(2, 28) == 59
assert day_of_year(2, 29) == 60
assert day_of_year(3, 1) == 61
assert day_of_year(12, 31) == 366
print("Day-of-year mapping OK")

# For a date, compute its day of year
def date_to_doy(d):
    return day_of_year(d.month, d.day)

# Generate all dates in the baseline range
baseline_dates_all = []  # from 1991-12-27 to 2003-01-05
d = date(1991, 12, 27)
end = date(2003, 1, 5)
while d <= end:
    baseline_dates_all.append(d)
    d += timedelta(days=1)
print(f"Baseline dates: {len(baseline_dates_all)} from {baseline_dates_all[0]} to {baseline_dates_all[-1]}")

# The baseline years are 1992-2002
baseline_years = range(1992, 2003)

# For each day of year d (1-366, d != 60), build pool dates
# A date t is in the pool for day-of-year d if there exists a baseline date b
# in 1992-2002 with day_of_year(b) == d and |t - b| <= 5 days

# Build a set of pool dates for each day-of-year
pool_dates_by_doy = {}

# First, find all baseline dates (in 1992-2002) by day-of-year
baseline_dates_by_doy = {}
for y in baseline_years:
    # Iterate through all dates in the year
    d = date(y, 1, 1)
    d_end = date(y, 12, 31)
    while d <= d_end:
        doy = date_to_doy(d)
        if doy not in baseline_dates_by_doy:
            baseline_dates_by_doy[doy] = []
        baseline_dates_by_doy[doy].append(d)
        d += timedelta(days=1)

print("Baseline dates by doy, doy count:", len(baseline_dates_by_doy))
print("Day 1 baseline dates:", [str(d) for d in baseline_dates_by_doy[1][:3]], "...")
print("Day 366 baseline dates:", [str(d) for d in baseline_dates_by_doy[366]])

# For each day-of-year, collect pool dates
all_pool_dates_by_doy = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for b in baseline_dates_by_doy.get(doy, []):
        for offset in range(-5, 6):
            t = b + timedelta(days=offset)
            if baseline_dates_all[0] <= t <= baseline_dates_all[-1]:
                pool_dates.add(t)
    all_pool_dates_by_doy[doy] = sorted(pool_dates)

# Verify some pools
print("\nDay 1 pool size:", len(all_pool_dates_by_doy[1]))
print("Day 1 pool dates (first 15):", [str(d) for d in all_pool_dates_by_doy[1][:15]])
print("Day 1 pool dates (last 15):", [str(d) for d in all_pool_dates_by_doy[1][-15:]])
print("Day 100 pool size:", len(all_pool_dates_by_doy[100]))
print("Day 366 pool size:", len(all_pool_dates_by_doy[366]))
print("Day 366 pool dates (first 5):", [str(d) for d in all_pool_dates_by_doy[366][:5]])
print("Day 366 pool dates (last 5):", [str(d) for d in all_pool_dates_by_doy[366][-5:]])
