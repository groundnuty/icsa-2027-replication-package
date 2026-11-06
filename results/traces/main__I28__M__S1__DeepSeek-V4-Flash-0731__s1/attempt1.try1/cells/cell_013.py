
from datetime import date, timedelta
import numpy as np

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# Extended baseline dates
base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
all_dates = []
d = base_start
while d <= base_end:
    all_dates.append(d)
    d += timedelta(days=1)
n_dates = len(all_dates)

# Map each date to its index in the array
date_to_idx = {d: i for i, d in enumerate(all_dates)}

# Define the official baseline dates (1992-01-01 to 2002-12-31)
baseline_1992_2002 = [d for d in all_dates if date(1992,1,1) <= d <= date(2002,12,31)]

# For each doy d (1-366, d≠60), find which dates contribute to its pool
# A date X contributes to pool d if there exists a baseline date D with doy(D)=d and |X-D| <= 5 days
pool_dates = {}  # doy -> set of date indices
for doy in range(1, 367):
    if doy == 60:
        continue
    pool = set()
    # Find baseline dates with this doy
    for D in baseline_1992_2002:
        if doy_of_date(D) == doy:
            # Include D-5 to D+5
            for k in range(-5, 6):
                X = D + timedelta(days=k)
                if X in date_to_idx:
                    pool.add(date_to_idx[X])
    pool_dates[doy] = sorted(pool)

# Check pool sizes
for doy in [1, 59, 60, 61, 153, 244, 366]:
    if doy in pool_dates:
        print(f"doy {doy}: pool size = {len(pool_dates[doy])}")
        # Show some dates in the pool
        idxs = pool_dates[doy][:5]
        print(f"  First 5 dates: {[all_dates[i].strftime('%Y-%m-%d') for i in idxs]}")
    else:
        print(f"doy {doy}: no pool")

# Check if day 60 is correctly excluded
print("\nChecking day 60 handling...")
print(f"Day 59 pool size: {len(pool_dates[59])}")
print(f"Day 61 pool size: {len(pool_dates[61])}")
