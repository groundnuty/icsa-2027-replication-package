
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict

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
all_dates = np.array(all_dates, dtype=object)
n_dates = len(all_dates)

# Baseline dates (1992-01-01 to 2002-12-31)
base_start_d = date(1992, 1, 1)
base_end_d = date(2002, 12, 31)
base_mask = np.array([base_start_d <= x <= base_end_d for x in all_dates])
base_dates = all_dates[base_mask]

# Map date to index
date_to_idx = {d: i for i, d in enumerate(all_dates)}

# For each doy, find baseline dates with that doy
doy_to_base_dates = defaultdict(list)
for y in base_dates:
    d = day_of_year_custom(y)
    doy_to_base_dates[d].append(y)

# For each doy, compute which date indices are in the pool
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

print("Pool masks computed.")
print(f"doy=1 pool size: {doy_to_pool_mask[1].sum()}")
print(f"doy=366 pool size: {doy_to_pool_mask[366].sum()}")
print(f"doy=59 pool size: {doy_to_pool_mask[59].sum()}")
print(f"doy=61 pool size: {doy_to_pool_mask[61].sum()}")

# Verify Feb 29 values are in pools of neighbors
# Feb 29, 1992: find its index
feb29_1992 = date(1992, 2, 29)
feb29_idx = date_to_idx[feb29_1992]
print(f"\nFeb 29, 1992 index: {feb29_idx}")
print(f"doy of Feb 29, 1992: {day_of_year_custom(feb29_1992)}")
print(f"Feb 29 in doy=59 pool: {doy_to_pool_mask[59][feb29_idx]}")
print(f"Feb 29 in doy=61 pool: {doy_to_pool_mask[61][feb29_idx]}")
print(f"Feb 29 in doy=60 pool: N/A (no pool for day 60)")

# Verify window extension dates
jan5_2003 = date(2003, 1, 5)
jan5_idx = date_to_idx[jan5_2003]
print(f"\nJan 5, 2003 in doy=366 pool: {doy_to_pool_mask[366][jan5_idx]}")
print(f"Jan 5, 2003 in doy=365 pool: {doy_to_pool_mask[365][jan5_idx]}")

dec27_1991 = date(1991, 12, 27)
dec27_idx = date_to_idx[dec27_1991]
print(f"Dec 27, 1991 in doy=1 pool: {doy_to_pool_mask[1][dec27_idx]}")
