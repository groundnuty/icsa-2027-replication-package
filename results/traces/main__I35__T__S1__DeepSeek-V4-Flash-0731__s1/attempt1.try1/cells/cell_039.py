
import numpy as np
import datetime
from collections import defaultdict

baseline_sst = np.load('/tmp/baseline_sst.npy')
baseline_times = np.load('/tmp/baseline_times.npy')
baseline_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in baseline_times]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

baseline_date_to_idx = {}
for i, d in enumerate(baseline_dates):
    baseline_date_to_idx[d] = i

# Build doy pools
baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

doy_dates = defaultdict(list)
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    doy_dates[doy].append(d)
    d += datetime.timedelta(days=1)

# Verify pool for doy=153 (June 1)
doy = 153
dates_with_doy = doy_dates[doy]
print(f"Dates with doy={doy}: {dates_with_doy}")

# The pool includes ±5 days around each of these dates
pool_dates = set()
for D in dates_with_doy:
    for offset in range(-5, 6):
        pool_dates.add(D + datetime.timedelta(days=offset))

print(f"Pool dates for doy={doy}: {len(pool_dates)}")
# Sort and show first few and last few
sorted_pool = sorted(pool_dates)
print(f"  First: {sorted_pool[0]} to {sorted_pool[10]}")
print(f"  Last: {sorted_pool[-11:]}")

# Verify that Feb 29 values are included in neighboring windows
# Check doy=59 (Feb 28) pool - should include Feb 29 values
doy59_pool_dates = set()
for D in doy_dates[59]:
    for offset in range(-5, 6):
        doy59_pool_dates.add(D + datetime.timedelta(days=offset))

feb29_dates_in_pool = [d for d in sorted(doy59_pool_dates) if d.month == 2 and d.day == 29]
print(f"\nDoy 59 pool contains Feb 29 dates: {feb29_dates_in_pool}")

# Check doy 61 pool
doy61_pool_dates = set()
for D in doy_dates[61]:
    for offset in range(-5, 6):
        doy61_pool_dates.add(D + datetime.timedelta(days=offset))

feb29_in_61 = [d for d in sorted(doy61_pool_dates) if d.month == 2 and d.day == 29]
print(f"Doy 61 pool contains Feb 29 dates: {feb29_in_61}")

# Verify that day 60 has no pool
print(f"\nDay 60 in doy_dates: {doy_dates.get(60, [])}")
