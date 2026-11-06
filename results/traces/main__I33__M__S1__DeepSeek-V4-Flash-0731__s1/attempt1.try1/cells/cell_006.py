
from datetime import datetime, timedelta
import numpy as np

# Define day-of-year mapping function
def day_of_year(year, month, day):
    """Map a date to day of year (1-366) as specified."""
    # Jan 1 = 1, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, ..., Dec 31 = 366
    # Non-leap years have no day 60
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        days_in_month[1] = 29
    return sum(days_in_month[:month-1]) + day

# Test the mapping
print(f"Jan 1: {day_of_year(1992, 1, 1)}")  # Should be 1
print(f"Feb 28: {day_of_year(1992, 2, 28)}")  # Should be 59
print(f"Feb 29: {day_of_year(1992, 2, 29)}")  # Should be 60
print(f"Mar 1: {day_of_year(1992, 3, 1)}")  # Should be 61
print(f"Dec 31: {day_of_year(1992, 12, 31)}")  # Should be 366
print(f"Feb 28 non-leap: {day_of_year(1993, 2, 28)}")  # Should be 59
print(f"Mar 1 non-leap: {day_of_year(1993, 3, 1)}")  # Should be 61

# Baseline period dates: 1991-12-27 to 2003-01-05
start = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += timedelta(days=1)
print(f"\nTotal baseline dates: {len(all_dates)}")

# For each day of year d (1-366), find which dates belong to its pool
# For day d, the pool consists of all dates within ±5 calendar days of any 
# baseline date (1992-01-01 to 2002-12-31) whose day of year is d

# First, for each baseline date (1992-01-01 to 2002-12-31), compute its day of year
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Map: day_of_year -> list of dates that are within ±5 days of a baseline date with that day of year
# Actually, let me think of this differently.
# For each day of year d, we need all dates X such that:
#   X is within ±5 calendar days of some baseline date B (1992-01-01 to 2002-12-31) where doy(B) = d
# So: for each baseline date B with doy(B)=d, take all dates B-5 through B+5

# Build a dictionary mapping each day of year to the set of all dates in its pool
from collections import defaultdict
doy_pool_dates = defaultdict(set)

d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d.year, d.month, d.day)
    for delta in range(-5, 6):
        date_in_pool = d + timedelta(days=delta)
        # Only include if within our loaded data range (which is 1991-12-27 to 2003-01-05)
        if start <= date_in_pool <= end:
            doy_pool_dates[doy].add(date_in_pool)
    d += timedelta(days=1)

# Check: day 60 should have no pool of its own
print(f"\nDay 60 pool size: {len(doy_pool_dates[60])}")

# Check some days
for d in [1, 59, 61, 366]:
    dates = sorted(doy_pool_dates[d])
    print(f"Day {d}: {len(dates)} dates, first: {dates[0]}, last: {dates[-1]}")

# Print number of dates for each day of year
for d in sorted(doy_pool_dates.keys()):
    if d != 60:
        print(f"Day {d}: {len(doy_pool_dates[d])} dates")
