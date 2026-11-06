
import numpy as np
import pandas as pd
from datetime import date, timedelta

def day_of_year_custom(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Generate all dates in the full window
start = date(1991, 12, 27)
end = date(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += timedelta(days=1)

print(f"Total dates in window: {len(all_dates)}")

# Baseline dates (1992-01-01 to 2002-12-31)
base_start = date(1992, 1, 1)
base_end = date(2002, 12, 31)
base_dates = [x for x in all_dates if base_start <= x <= base_end]
print(f"Baseline dates: {len(base_dates)}")

# For each doy, compute the pool of dates
# Pool for doy d = {x in all_dates : exists y in base_dates with doy(y)=d and |x-y| <= 5 days}

# First, for each doy, find all baseline dates with that doy
from collections import defaultdict
doy_to_base_dates = defaultdict(list)
for y in base_dates:
    d = day_of_year_custom(y)
    doy_to_base_dates[d].append(y)

# For each doy, compute pool
doy_to_pool = {}
for d in range(1, 367):
    if d == 60:
        continue  # no pool for day 60
    pool_dates = set()
    for y in doy_to_base_dates[d]:
        # Add all dates within 5 days
        for offset in range(-5, 6):
            x = y + timedelta(days=offset)
            if start <= x <= end:
                pool_dates.add(x)
    doy_to_pool[d] = sorted(pool_dates)
    #print(f"doy={d}: {len(pool_dates)} dates")

# Check some pools
print(f"\ndoy=1 pool size: {len(doy_to_pool[1])}")
print(f"  First few: {doy_to_pool[1][:5]}")
print(f"  Last few: {doy_to_pool[1][-5:]}")
print(f"doy=366 pool size: {len(doy_to_pool[366])}")
print(f"  First few: {doy_to_pool[366][:5]}")
print(f"  Last few: {doy_to_pool[366][-5:]}")
print(f"doy=59 pool size: {len(doy_to_pool[59])}")
print(f"  First few: {doy_to_pool[59][:5]}")
print(f"  Last few: {doy_to_pool[59][-5:]}")
print(f"doy=61 pool size: {len(doy_to_pool[61])}")
print(f"  First few: {doy_to_pool[61][:5]}")
print(f"  Last few: {doy_to_pool[61][-5:]}")
