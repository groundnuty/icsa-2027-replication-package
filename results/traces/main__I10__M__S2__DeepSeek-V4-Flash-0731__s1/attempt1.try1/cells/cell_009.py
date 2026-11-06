
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

# Pool dates
pool_dates_actual = []
d = date(1991, 12, 27)
while d <= date(2003, 1, 5):
    pool_dates_actual.append(d)
    d += timedelta(days=1)

# Build doy -> pool date indices, excluding doy 60
doy_to_pool_idx = defaultdict(list)
for pi, t in enumerate(pool_dates_actual):
    for offset in range(-5, 6):
        b = t + timedelta(days=offset)
        if b in baseline_dates_set:
            d = doy_map(b)
            if d != 60:  # exclude day 60
                doy_to_pool_idx[d].append(pi)

# Verify no doy 60
print("Day 60 entries:", len(doy_to_pool_idx.get(60, [])))

# Check some pools
for d in [1, 59, 61, 366]:
    print(f"doy {d}: {len(doy_to_pool_idx[d])} entries")

# Verify: doy 59 should include Feb 24-28 in each baseline year, plus adjacent from other years
# Let's check what dates are in pool 59
# Baseline dates with doy 59 = Feb 28 in each year 1992-2002
# Their windows: Feb 23 - Mar 5 in each year
# Total: 11 years × 11 days = 121
# Plus from doy 58 baseline dates (Feb 27): their windows include Feb 28 = doy 59
# Wait no, pool 59 includes dates within ±5 of Feb 28 in each year. 
# Feb 28 baseline window: Feb 23 - Mar 5 = 11 dates per year, 11 years = 121
# But also, dates within ±5 of other baseline dates with doy != 59 don't add to pool 59
# Actually they do. pool 59 = dates within ±5 of baseline dates with doy 59 = Feb 28 in each year.
# So pool 59 = all dates from Feb 23 to Mar 5 in each year 1992-2002.
# But wait, those dates overlap with Feb 29 windows and Mar 1 windows...

# Let me just verify by checking what dates are in pool 59
for t in pool_dates_actual:
    if 59 in doy_to_pool_idx[59] if False else False:
        pass

# Actually let me just check the count of unique pool dates for doy 59
unique_pool_59 = set(doy_to_pool_idx[59])
print("Unique pool dates for doy 59:", len(unique_pool_59))
print("doy 59 pool indices sample:", sorted(unique_pool_59)[:15])
