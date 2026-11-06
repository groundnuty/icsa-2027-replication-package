
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

# Verify pool construction for doy 1
days_before_month = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_date(dt):
    return days_before_month[dt.month - 1] + dt.day

# Reconstruct dates
base_start = datetime(1991, 12, 27)
base_end = datetime(2003, 1, 5)
all_dates = []
d = base_start
while d <= base_end:
    all_dates.append(d)
    d += timedelta(days=1)

# Baseline dates (1992-2002)
baseline_dates = [dt for dt in all_dates if datetime(1992,1,1) <= dt <= datetime(2002,12,31)]
print("Num baseline dates:", len(baseline_dates))

# For doy 1, which baseline dates have doy 1?
doy1_baseline = [b for b in baseline_dates if doy_from_date(b) == 1]
print("Baseline dates with doy 1:", [(b.date().isoformat()) for b in doy1_baseline])

# What dates are within ±5 days of each?
pool_dates = set()
for b in doy1_baseline:
    for i in range(-5, 6):
        pool_dates.add(b + timedelta(days=i))

# Filter to our extended range
pool_dates_in_range = sorted([d for d in pool_dates if base_start <= d <= base_end])
print("Pool dates for doy 1:", len(pool_dates_in_range))
print("First few:", [d.date().isoformat() for d in pool_dates_in_range[:15]])
print("Last few:", [d.date().isoformat() for d in pool_dates_in_range[-15:]])

# Now let's also verify day 59 and day 61 pools to check Feb 29 handling
print("\n--- Day 59 pool ---")
doy59_baseline = [b for b in baseline_dates if doy_from_date(b) == 59]
print("Baseline dates with doy 59:", [b.date().isoformat() for b in doy59_baseline])
pool_59 = set()
for b in doy59_baseline:
    for i in range(-5, 6):
        pool_59.add(b + timedelta(days=i))
pool_59_in_range = sorted([d for d in pool_59 if base_start <= d <= base_end])
# Check if any Feb 29 dates are in the pool
feb29 = [d for d in pool_59_in_range if d.month == 2 and d.day == 29]
print("Feb 29 dates in pool 59:", [d.date().isoformat() for d in feb29])

print("\n--- Day 61 pool ---")
doy61_baseline = [b for b in baseline_dates if doy_from_date(b) == 61]
print("Baseline dates with doy 61:", [b.date().isoformat() for b in doy61_baseline])
pool_61 = set()
for b in doy61_baseline:
    for i in range(-5, 6):
        pool_61.add(b + timedelta(days=i))
pool_61_in_range = sorted([d for d in pool_61 if base_start <= d <= base_end])
feb29_61 = [d for d in pool_61_in_range if d.month == 2 and d.day == 29]
print("Feb 29 dates in pool 61:", [d.date().isoformat() for d in feb29_61])
