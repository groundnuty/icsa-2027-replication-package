
import numpy as np
from datetime import date, timedelta

def doy_map(d):
    """Map date to day of year 1-366 (always treating Feb as 29 days)."""
    months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(months[:d.month-1]) + d.day

# Verify some mappings
print("Jan 1:", doy_map(date(2000,1,1)))   # 1
print("Feb 28:", doy_map(date(2000,2,28)))  # 59
print("Feb 29:", doy_map(date(2000,2,29)))  # 60
print("Mar 1:", doy_map(date(2000,3,1)))    # 61
print("Dec 31:", doy_map(date(2000,12,31))) # 366

# Baseline dates: 1992-01-01 to 2002-12-31
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# For each baseline date b, the window [b-5, b+5] contributes to pool(doy(b))
# Build mapping: pool_dates[d] = list of dates in pool range that belong to pool d
# Actually, let's build the reverse: for each date t in pool range, which pools does it belong to?

pool_dates_all = []  # list of all dates in pool range
d = date(1991, 12, 27)
while d <= date(2003, 1, 5):
    pool_dates_all.append(d)
    d += timedelta(days=1)
print("Total pool dates:", len(pool_dates_all))

# For each pool date t, find baseline dates b with |t-b| <= 5
# Generate set of baseline dates
baseline_dates_set = set()
d = baseline_start
while d <= baseline_end:
    baseline_dates_set.add(d)
    d += timedelta(days=1)
print("Total baseline dates:", len(baseline_dates_set))

# For each pool date t, find which baseline dates it's within 5 days of
from collections import defaultdict
date_to_pool = {}  # date -> set of doy values

for t in pool_dates_all:
    pools_for_t = set()
    for offset in range(-5, 6):
        b = t + timedelta(days=offset)
        if b in baseline_dates_set:
            pools_for_t.add(doy_map(b))
    date_to_pool[t] = pools_for_t

# Check a few
for t in [date(1992,6,15), date(1991,12,27), date(1991,12,31), date(2003,1,1), date(2003,1,5)]:
    print(t, "->", sorted(date_to_pool[t]))
