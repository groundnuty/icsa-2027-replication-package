
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict

def day_of_year_custom(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Recompute setup
start = date(1991, 12, 27)
end = date(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += timedelta(days=1)
all_dates = np.array(all_dates, dtype=object)
n_dates = len(all_dates)

base_start_d = date(1992, 1, 1)
base_end_d = date(2002, 12, 31)
base_mask = np.array([base_start_d <= x <= base_end_d for x in all_dates])
date_to_idx = {d: i for i, d in enumerate(all_dates)}

doy_to_base_dates = defaultdict(list)
for y in all_dates[base_mask]:
    d = day_of_year_custom(y)
    doy_to_base_dates[d].append(y)

doy_to_pool_mask = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_mask = np.zeros(n_dates, dtype=bool)
    for y in doy_to_base_dates[d]:
        y_idx = date_to_idx[y]
        lo = max(0, y_idx - 5)
        hi = min(n_dates, y_idx + 6)
        pool_mask[lo:hi] = True
    doy_to_pool_mask[d] = pool_mask

# Check doy=153 (June 1)
doy = 153
pool_dates = all_dates[doy_to_pool_mask[doy]]
print(f"doy={doy} pool size: {len(pool_dates)}")
# Show which years are included
years = sorted(set(d.year for d in pool_dates))
print(f"Years in pool: {years}")

# Check that June 1 of each year 1992-2002 is in the pool
for year in range(1992, 2003):
    d = date(year, 6, 1)
    assert day_of_year_custom(d) == doy
    idx = date_to_idx[d]
    assert doy_to_pool_mask[doy][idx], f"June 1, {year} not in pool!"

# Check window dates
# June 1, 1992 - 5 = May 27, 1992
d = date(1992, 5, 27)
idx = date_to_idx[d]
assert doy_to_pool_mask[doy][idx], f"May 27, 1992 not in pool!"

# June 1, 2002 + 5 = June 6, 2002
d = date(2002, 6, 6)
idx = date_to_idx[d]
assert doy_to_pool_mask[doy][idx], f"June 6, 2002 not in pool!"

# Check that a date not near any June 1 in 1992-2002 is not in the pool
d = date(1992, 7, 1)
idx = date_to_idx[d]
assert not doy_to_pool_mask[doy][idx], f"July 1, 1992 should not be in pool!"

print("Pool for doy=153 verified correctly.")

# Also check doy=1 (Jan 1)
doy = 1
pool_dates = all_dates[doy_to_pool_mask[doy]]
print(f"\ndoy={doy} pool size: {len(pool_dates)}")
years = sorted(set(d.year for d in pool_dates))
print(f"Years in pool: {years}")

# Check boundary
# Jan 1, 1992 - 5 = Dec 27, 1991 (window extension)
d = date(1991, 12, 27)
idx = date_to_idx[d]
assert doy_to_pool_mask[doy][idx], f"Dec 27, 1991 not in pool!"
print("Window extension for doy=1 verified.")

# Check doy=366 (Dec 31)
doy = 366
pool_dates = all_dates[doy_to_pool_mask[doy]]
print(f"\ndoy={doy} pool size: {len(pool_dates)}")
years = sorted(set(d.year for d in pool_dates))
print(f"Years in pool: {years}")

# Check boundary
# Dec 31, 2002 + 5 = Jan 5, 2003 (window extension)
d = date(2003, 1, 5)
idx = date_to_idx[d]
assert doy_to_pool_mask[doy][idx], f"Jan 5, 2003 not in pool!"
print("Window extension for doy=366 verified.")

# Check doy=60 has no pool
assert 60 not in doy_to_pool_mask
print("\nDay 60 has no pool. Verified.")

# Verify Feb 29 in pools of neighbors
feb29_1992 = date(1992, 2, 29)
idx = date_to_idx[feb29_1992]
print(f"Feb 29, 1992 in doy=59 pool: {doy_to_pool_mask[59][idx]}")
print(f"Feb 29, 1992 in doy=61 pool: {doy_to_pool_mask[61][idx]}")
