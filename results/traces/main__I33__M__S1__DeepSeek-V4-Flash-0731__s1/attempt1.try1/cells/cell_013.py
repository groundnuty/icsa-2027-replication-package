
from datetime import datetime, timedelta
from collections import defaultdict

starts = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def doy(month, day):
    return starts[month] + day

# Data range
data_start = datetime(1991, 12, 27)
data_end = datetime(2003, 1, 5)

# Baseline range
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Build mapping: date -> set of day-of-year pools it belongs to
# For each date X, X belongs to pool d if there's a baseline date B with doy(B)=d and |X-B|<=5
# Equivalently: for each baseline date B, all dates in [B-5, B+5] belong to pool doy(B)

# Build: for each day-of-year d, the set of dates in its pool
doy_pool_dates = defaultdict(set)

# For each baseline date B
d = baseline_start
while d <= baseline_end:
    d_doy = doy(d.month, d.day)
    if d_doy != 60:  # Day 60 gets no pool
        for delta in range(-5, 6):
            date_in_pool = d + timedelta(days=delta)
            if data_start <= date_in_pool <= data_end:
                doy_pool_dates[d_doy].add(date_in_pool)
    d += timedelta(days=1)

# Now, build reverse mapping: date -> list of day-of-year pools
date_to_doy_pools = defaultdict(list)
for d_doy, dates in doy_pool_dates.items():
    for dt in dates:
        date_to_doy_pools[dt].append(d_doy)

# Check sizes
print(f"Number of unique dates: {len(date_to_doy_pools)}")
# For each date, how many pools does it belong to?
pool_counts = [len(pools) for pools in date_to_doy_pools.values()]
print(f"Pool count per date: min={min(pool_counts)}, max={max(pool_counts)}, avg={np.mean(pool_counts):.1f}")

# Total (date, pool) pairs
total_pairs = sum(pool_counts)
print(f"Total (date, pool) pairs: {total_pairs}")

# Number of days of year with pools
print(f"Days of year with pools: {len(doy_pool_dates)}")

# Check: which day-of-year values have no pools? (Should only be 60)
all_doy = set(range(1, 367))
no_pool = all_doy - set(doy_pool_dates.keys())
print(f"Day-of-year values without pools: {sorted(no_pool)}")
