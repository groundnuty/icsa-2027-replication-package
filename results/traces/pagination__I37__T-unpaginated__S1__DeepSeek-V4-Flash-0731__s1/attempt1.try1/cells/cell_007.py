
import datetime
import numpy as np

# Day of year mapping
def doy_from_date(date):
    """Map a date to day of year 1-366 based on month/day (as if every year were leap)."""
    month = date.month
    day = date.day
    # Days before each month in a leap year
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[month-1] + day

# Verify
assert doy_from_date(datetime.date(2000, 1, 1)) == 1
assert doy_from_date(datetime.date(2000, 2, 28)) == 59
assert doy_from_date(datetime.date(2000, 2, 29)) == 60
assert doy_from_date(datetime.date(2000, 3, 1)) == 61
assert doy_from_date(datetime.date(2000, 12, 31)) == 366
assert doy_from_date(datetime.date(2001, 2, 28)) == 59
assert doy_from_date(datetime.date(2001, 3, 1)) == 61  # no day 60 for non-leap

# Baseline period
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)

# All dates in the extended baseline
all_dates = []
d = baseline_start
while d <= baseline_end:
    all_dates.append(d)
    d += datetime.timedelta(days=1)

# For each day of year d (1-366, excluding 60), find the dates that contribute
# The pool for day-of-year d consists of dates within ±5 calendar days of any baseline date (1992-2002) with doy d

# First find all baseline dates in 1992-2002 with each doy
doy_to_dates = {i: [] for i in range(1, 367)}
for date in all_dates:
    if 1992 <= date.year <= 2002:
        d = doy_from_date(date)
        doy_to_dates[d].append(date)

# For each doy, expand to include ±5 days
doy_to_pool_dates = {i: set() for i in range(1, 367)}
for d in range(1, 367):
    if d == 60:
        continue
    for center_date in doy_to_dates[d]:
        for offset in range(-5, 6):
            doy_to_pool_dates[d].add(center_date + datetime.timedelta(days=offset))

# Check some examples
print(f"Day 1 pool dates count: {len(doy_to_pool_dates[1])}")
print(f"Day 59 pool dates count: {len(doy_to_pool_dates[59])}")
print(f"Day 61 pool dates count: {len(doy_to_pool_dates[61])}")
print(f"Day 366 pool dates count: {len(doy_to_pool_dates[366])}")

# Check: which days have no dates? (should be only day 60 and any others)
empty_days = [d for d in range(1, 367) if d != 60 and len(doy_to_pool_dates[d]) == 0]
print(f"Empty doy pools (excluding 60): {empty_days}")

# Check what dates are in day 1's pool
d1_dates = sorted(doy_to_pool_dates[1])
print(f"Day 1 pool dates (first few): {d1_dates[:10]}")
print(f"Day 1 pool dates (last few): {d1_dates[-10:]}")

# Check day 366's pool
d366_dates = sorted(doy_to_pool_dates[366])
print(f"Day 366 pool dates (first few): {d366_dates[:10]}")
print(f"Day 366 pool dates (last few): {d366_dates[-10:]}")
