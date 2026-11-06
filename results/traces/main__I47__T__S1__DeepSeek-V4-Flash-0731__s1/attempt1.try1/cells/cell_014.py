
import numpy as np
from datetime import datetime, timedelta

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

# Generate all baseline dates
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

from collections import defaultdict
doy_to_baseline_dates = defaultdict(list)
d = baseline_start
while d <= baseline_end:
    doy = date_to_doy(d)
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

# For each day-of-year d, the pool includes all dates X in extended range
# such that X is within ±5 days of some baseline date with doy=d
# The extended range is [1991-12-27, 2003-01-05]

# For each doy d, compute the set of dates in the pool
ext_start = datetime(1991, 12, 27)
ext_end = datetime(2003, 1, 5)

# For efficiency, for each doy d, we know which dates fall in the pool:
# For each baseline date Y with doy=d, the range [Y-5, Y+5]
# The union of these ranges gives the pool dates for doy d

# Let's compute for a sample doy first
def get_pool_dates(doy):
    dates = set()
    for Y in doy_to_baseline_dates.get(doy, []):
        for i in range(-5, 6):
            dates.add(Y + timedelta(days=i))
    return sorted(dates)

# Sample check for doy 153 (June 1)
pool_153 = get_pool_dates(153)
print(f"Pool for doy 153: {pool_153[:5]} ... {pool_153[-5:]}")
print(f"Number of dates in pool 153: {len(pool_153)}")

# For each doy, the expected number should be 11 years * 11 days = 121 dates
# (some might overlap if pools overlap)

# Check doy 60 (Feb 29) - should not have a pool
print(f"Pool for doy 60 (should be empty): {get_pool_dates(60)}")

# Check doy 59 (Feb 28)
pool_59 = get_pool_dates(59)
print(f"Pool for doy 59: first few = {pool_59[:3]}, last few = {pool_59[-3:]}, count = {len(pool_59)}")
# Check if Feb 29 of leap years is in pool 59
for Y in [datetime(1992, 2, 29), datetime(1996, 2, 29), datetime(2000, 2, 29)]:
    print(f"  Feb 29 {Y.year} in pool 59: {Y in pool_59}")

# Check doy 61 (Mar 1)
pool_61 = get_pool_dates(61)
print(f"Pool for doy 61: count = {len(pool_61)}")
for Y in [datetime(1992, 2, 29), datetime(1996, 2, 29), datetime(2000, 2, 29)]:
    print(f"  Feb 29 {Y.year} in pool 61: {Y in pool_61}")
