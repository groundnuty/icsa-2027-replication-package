import numpy as np
from datetime import datetime, timedelta

# Day-of-year mapping
def day_of_year(dt):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:dt.month-1]) + dt.day

# Generate all dates in the extraction range
start = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += timedelta(days=1)
print(f"Total extraction dates: {len(all_dates)}")

# Identify baseline dates (1992-01-01 to 2002-12-31)
base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)
baseline_dates = [dt for dt in all_dates if base_start <= dt <= base_end]
print(f"Baseline dates: {len(baseline_dates)}")

# For each baseline date, compute its day-of-year
base_doy = [day_of_year(dt) for dt in baseline_dates]

# Build the pool indices for each day-of-year
# For day d, find all baseline dates with that DOY, then include ±5 days
from collections import defaultdict

# Map from day-of-year to set of indices in all_dates
doy_pools = defaultdict(list)  # doy -> list of indices into baseline_data

for d, dt in enumerate(baseline_dates):
    doy = base_doy[d]
    if doy == 60:
        continue  # day 60 gets no pool
    # For this baseline date, include all dates in the extraction range within ±5 days
    # The baseline date is baseline_dates[d], which is all_dates[d + offset]
    # Find the index in all_dates
    base_idx_in_all = all_dates.index(dt)
    # Add indices from base_idx_in_all - 5 to base_idx_in_all + 5 (within range)
    for i in range(max(0, base_idx_in_all - 5), min(len(all_dates), base_idx_in_all + 6)):
        doy_pools[doy].append(i)

# Convert to unique sorted lists
for doy in doy_pools:
    doy_pools[doy] = sorted(set(doy_pools[doy]))

# Check pool sizes
print(f"Number of day-of-year pools: {len(doy_pools)}")
for doy in [1, 59, 61, 100, 200, 300, 366]:
    if doy in doy_pools:
        print(f"DOY {doy}: {len(doy_pools[doy])} dates")
    else:
        print(f"DOY {doy}: NO POOL")
