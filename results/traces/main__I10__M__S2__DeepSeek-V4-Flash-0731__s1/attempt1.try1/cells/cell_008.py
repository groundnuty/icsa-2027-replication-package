
import numpy as np
from datetime import date, timedelta
from collections import defaultdict

def doy_map(d):
    months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(months[:d.month-1]) + d.day

# Build baseline dates set
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)
baseline_dates_set = set()
d = baseline_start
while d <= baseline_end:
    baseline_dates_set.add(d)
    d += timedelta(days=1)

# For each pool date (index in pool_local), determine which doy pools it belongs to
# pool_dates = the actual date objects for pool period
pool_dates_actual = []  # list of date objects
d = date(1991, 12, 27)
while d <= date(2003, 1, 5):
    pool_dates_actual.append(d)
    d += timedelta(days=1)
print("len pool_dates_actual:", len(pool_dates_actual))

# Build: for each pool date index, set of doy values it contributes to
date_to_doy_set = {}
for t in pool_dates_actual:
    pools = set()
    for offset in range(-5, 6):
        b = t + timedelta(days=offset)
        if b in baseline_dates_set:
            pools.add(doy_map(b))
    date_to_doy_set[t] = pools

# Now build: for each doy d, the list of pool date indices (local to pool array)
doy_to_pool_idx = defaultdict(list)  # doy -> list of pool-local indices
for pi, t in enumerate(pool_dates_actual):
    for d in date_to_doy_set[t]:
        doy_to_pool_idx[d].append(pi)

# Check sizes
for d in [1, 2, 59, 60, 61, 366]:
    print(f"doy {d}: {len(doy_to_pool_idx[d])} pool entries")

# Day 60 should have no entries
print("Day 60 entries:", len(doy_to_pool_idx.get(60, [])))
