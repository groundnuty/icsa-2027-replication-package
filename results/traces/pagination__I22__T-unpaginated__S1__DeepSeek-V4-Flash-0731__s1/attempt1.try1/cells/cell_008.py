
import numpy as np
import datetime

def day_of_year(date):
    y, m, d = date.year, date.month, date.day
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    doy = sum(months[:m-1]) + d
    if m > 2 and is_leap:
        doy += 1
    if not is_leap and m > 2:
        doy += 1
    return doy

# Baseline dates: 1992-01-01 to 2002-12-31
baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

# All dates from 1991-12-27 to 2003-01-05
all_start = datetime.date(1991, 12, 27)
all_end = datetime.date(2003, 1, 5)

# Build list of all dates
all_dates = []
d = all_start
while d <= all_end:
    all_dates.append(d)
    d += datetime.timedelta(days=1)

# Map date -> day of year
doy_map = {d: day_of_year(d) for d in all_dates}

# For each day-of-year d (1-366, excl 60), find the set of dates contributing to its pool
# A date x contributes to day d's pool if there exists a baseline date y with doy(y)=d and |x-y|<=5
pool_dates = {}  # doy -> set of dates
for doy in range(1, 367):
    if doy == 60:
        continue
    # Find baseline dates with this day of year
    centers = []
    dy = baseline_start
    while dy <= baseline_end:
        if day_of_year(dy) == doy:
            centers.append(dy)
        dy += datetime.timedelta(days=1)
    
    # Union of ±5 day windows around centers
    pool = set()
    for c in centers:
        for k in range(-5, 6):
            x = c + datetime.timedelta(days=k)
            pool.add(x)
    pool_dates[doy] = pool

# Check: how many unique dates across all pools
all_pool_dates = set()
for pool in pool_dates.values():
    all_pool_dates |= pool

print(f'Total unique dates in all pools: {len(all_pool_dates)}')
print(f'Range: {min(all_pool_dates)} to {max(all_pool_dates)}')

# Check: how many days per doy pool
sizes = {d: len(p) for d, p in pool_dates.items()}
print(f'Pool size range: {min(sizes.values())} to {max(sizes.values())}')
print(f'Day 1 pool size: {sizes[1]}')
print(f'Day 366 pool size: {sizes[366]}')

# Check if all dates in all_pool_dates are within all_start to all_end
print(f'All pool dates within range: {min(all_pool_dates) >= all_start and max(all_pool_dates) <= all_end}')
