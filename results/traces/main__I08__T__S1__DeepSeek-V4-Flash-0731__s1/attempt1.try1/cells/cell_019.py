
import numpy as np
import datetime as dt

def day_of_year(ts):
    d = dt.datetime.fromtimestamp(ts.astype('datetime64[ns]').astype(np.int64) / 1e9, tz=dt.timezone.utc)
    year = d.year
    month = d.month
    day = d.day
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month > 2:
        std_doy += 1
    return std_doy

base_data = np.load('/tmp/base_data.npy')
base_times = np.load('/tmp/base_times.npy')
base_doy = np.load('/tmp/base_doy.npy')

# Find indices of baseline dates (1992-2002)
base_start = np.datetime64('1992-01-01')
base_end = np.datetime64('2002-12-31')
is_baseline = (base_times >= base_start) & (base_times <= base_end)
baseline_idx = np.where(is_baseline)[0]

# For each day-of-year, build the pool of indices
# Pool for day-of-year d: all indices t in [0, 4027] such that
# there exists a baseline index i (in baseline period) with base_doy[i]=d
# and |base_times[t] - base_times[i]| <= 5 days

# Precompute date differences in days
# Convert times to days since epoch for easy comparison
epoch = np.datetime64('1970-01-01')
base_days = (base_times - epoch).astype(np.int64) // (24*3600*10**9)  # days since epoch

print("Base days range:", base_days[0], base_days[-1])

# Build pools
pools = {}  # day_of_year -> list of indices

for d in range(1, 367):
    if d == 60:
        continue
    # Find baseline indices with this day-of-year
    d_indices = baseline_idx[base_doy[baseline_idx] == d]
    if len(d_indices) == 0:
        pools[d] = []
        continue
    
    # For each such index, find all dates within ±5 days
    pool_set = set()
    for i in d_indices:
        t_i = base_days[i]
        mask = np.abs(base_days - t_i) <= 5
        pool_set.update(np.where(mask)[0].tolist())
    
    pools[d] = sorted(pool_set)

# Check pool sizes
for d in [1, 2, 59, 61, 100, 153, 200, 244, 365, 366]:
    print(f"Day {d}: pool size = {len(pools[d])}")
    if len(pools[d]) > 0:
        idx = pools[d][0]
        print(f"  First index: {idx}, date: {base_times[idx]}")
        idx = pools[d][-1]
        print(f"  Last index: {idx}, date: {base_times[idx]}")

# Save pools
np.save('/tmp/pools_dict.npy', np.array(list(pools.items()), dtype=object), allow_pickle=True)

# Also save base_days for later
np.save('/tmp/base_days.npy', base_days)
