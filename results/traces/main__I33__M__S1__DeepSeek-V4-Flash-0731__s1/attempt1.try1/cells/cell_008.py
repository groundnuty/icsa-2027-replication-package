
from datetime import datetime, timedelta
from collections import defaultdict

starts = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def doy(month, day):
    return starts[month] + day

# Baseline dates: 1992-01-01 to 2002-12-31
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Data range: 1991-12-27 to 2003-01-05
data_start = datetime(1991, 12, 27)
data_end = datetime(2003, 1, 5)

# Build pools for each day of year
# For day d (1-366, d != 60), the pool is all dates within ±5 days of any 
# baseline date with doy = d

doy_pool_dates = defaultdict(set)

# Iterate over baseline dates
d = baseline_start
while d <= baseline_end:
    d_doy = doy(d.month, d.day)
    if d_doy != 60:  # Skip Feb 29 baseline dates for their own pool
        for delta in range(-5, 6):
            date_in_pool = d + timedelta(days=delta)
            if data_start <= date_in_pool <= data_end:
                doy_pool_dates[d_doy].add(date_in_pool)
    d += timedelta(days=1)

# Verify day 60 has no pool
print(f"Day 60 pool: {len(doy_pool_dates.get(60, set()))} dates")

# Check pool sizes for various days
for d in [1, 59, 61, 365, 366]:
    dates = sorted(doy_pool_dates[d])
    print(f"Day {d}: {len(dates)} dates, first: {dates[0].date()}, last: {dates[-1].date()}")

# Check: Feb 29 values should be in pools of days 59 and 61
# Find all Feb 29 dates in the baseline data range
feb29_dates = []
d = data_start
while d <= data_end:
    if d.month == 2 and d.day == 29:
        feb29_dates.append(d)
    d += timedelta(days=1)
print(f"\nFeb 29 dates in data range: {[x.date() for x in feb29_dates]}")

# Check if these are in pools for days 59 and 61
for fd in feb29_dates:
    in_59 = fd in doy_pool_dates[59]
    in_61 = fd in doy_pool_dates[61]
    print(f"  {fd.date()}: in day 59 pool: {in_59}, in day 61 pool: {in_61}")
