
import numpy as np
from datetime import datetime, date, timedelta

def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month-1]) + day
    return doy

# For each day-of-year d (1-366, except 60), find which dates (in baseline range) belong to its pool
# Baseline dates: 1992-01-01 to 2002-12-31
# Each baseline date y with doy=d has window [y-5, y+5]
# Pool for d = union of all such windows

# Let's map each date in the overall time range to its doy
# and determine for each doy which dataset time indices contribute

# Actually, let me think of it differently. For a given doy d, for each year y in [1992, 2002]:
# - find the date in year y with doy d
# - window is [that date - 5 days, that date + 5 days]
# All dates in these windows contribute to pool for d

# Let me first compute, for each year 1992-2002 and each doy, the date
from datetime import date as dt_date

# Generate all dates in the baseline extended period
baseline_start = dt_date(1991, 12, 27)
baseline_end = dt_date(2003, 1, 5)

# Create mapping from date to day-of-year
def date_to_doy(d):
    return day_of_year(d.month, d.day)

# For each doy d (1-366 except 60), find the dates in the pool
# Actually, let's do this: for each doy d, find all dates t such that 
# t is within 5 days of a baseline date y (1992-01-01 to 2002-12-31) with doy(y)=d

# First, let's generate all dates in the baseline extended range
all_dates = []
d = baseline_start
while d <= baseline_end:
    all_dates.append(d)
    d += timedelta(days=1)

print(f"Total dates in baseline extended range: {len(all_dates)}")

# For each doy, find baseline dates with that doy
from collections import defaultdict
doy_to_baseline_dates = defaultdict(list)
d = dt_date(1992, 1, 1)
while d <= dt_date(2002, 12, 31):
    doy = date_to_doy(d)
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

# Now for each doy, collect all dates in pool
doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool = set()
    for bd in doy_to_baseline_dates[doy]:
        for i in range(-5, 6):
            pool.add(bd + timedelta(days=i))
    doy_to_pool_dates[doy] = sorted(pool)

# Check some examples
print("doy 1 pool size:", len(doy_to_pool_dates[1]))
print("doy 1 first dates:", doy_to_pool_dates[1][:3])
print("doy 1 last dates:", doy_to_pool_dates[1][-3:])
print()
print("doy 59 pool size:", len(doy_to_pool_dates[59]))
print("doy 61 pool size:", len(doy_to_pool_dates[61]))
print("doy 366 pool size:", len(doy_to_pool_dates[366]))
print("doy 366 first:", doy_to_pool_dates[366][:2], "last:", doy_to_pool_dates[366][-2:])

# For Feb 28 (doy 59): 11 years of Feb 28, each with ±5 days window
# For non-leap years, Feb 28 window would be Feb 23 to Mar 5
# For leap years, Feb 28 window would be Feb 23 to Mar 4 (since Mar 5 = doy 64)

# Verify: pool for doy 59 should include Feb 29 (doy 60) values
# Let's check: for baseline date 1992-02-28 (doy 59 since 1992 is leap... wait)
# 1992 is a leap year. Feb 28 1992 has doy 59. Window: Feb 23 to Mar 4.
# Feb 29 1992 has doy 60. It's in the window of Feb 28 (within 1 day). Good.
# Also Mar 1 1992 has doy 61. It's in the window (Feb 28 + 2 = Mar 1). Good.

print("\nCheck: pool for doy 59 includes Feb 29 dates:")
feb29_in_pool59 = [d for d in doy_to_pool_dates[59] if d.month==2 and d.day==29]
print("Feb 29 dates in doy 59 pool:", feb29_in_pool59)
