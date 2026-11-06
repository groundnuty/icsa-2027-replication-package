
import numpy as np
import pandas as pd

baseline_data = np.load('/tmp/baseline_data.npy').astype(np.float64)
baseline_times = np.load('/tmp/baseline_times.npy').astype('datetime64[D]')

# Check a specific cell that should have NaN threshold
# First, let me find the 307 cells with NaN threshold
# Let me recompute for a single day

time_index_map = {}
for i, t in enumerate(baseline_times):
    time_index_map[t] = i

def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

# Build pool for day 200
d = 200
indices = set()
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
for year in range(1992, 2003):
    remaining = d
    month = 0
    while remaining > month_days[month]:
        remaining -= month_days[month]
        month += 1
    day = remaining
    month += 1
    
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    if month == 2 and day == 29 and not is_leap:
        continue
    
    b_date = np.datetime64(f'{year}-{month:02d}-{day:02d}', 'D')
    for offset in range(-5, 6):
        date_i = b_date + np.timedelta64(offset, 'D')
        if date_i in time_index_map:
            indices.add(time_index_map[date_i])

print(f"Pool for day {d}: {len(indices)} indices")
pool_idx = sorted(indices)
print("First few:", pool_idx[:5])
print("Last few:", pool_idx[-5:])

# Check the actual dates
for idx in pool_idx[:3]:
    print(f"  Index {idx}: date {baseline_times[idx]}")

# Check if these have valid data
pool_data = baseline_data[pool_idx, :, :]
print("Pool data shape:", pool_data.shape)
print("Pool data NaN count:", np.isnan(pool_data).sum())

# Check a specific cell - let me find one with NaN threshold
sea_mask = np.load('/tmp/sea_mask.npy')
n_lat, n_lon = sea_mask.shape

# Compute threshold for this day
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i, j]:
            vals = pool_data[:, i, j]
            vals = vals[~np.isnan(vals)]
            if len(vals) == 0:
                print(f"Cell ({i},{j}) has empty pool for day {d}")
                # Check if this cell has valid baseline data
                print(f"  All baseline NaN for this cell: {np.all(np.isnan(baseline_data[:, i, j]))}")
                print(f"  Baseline valid count: {np.sum(~np.isnan(baseline_data[:, i, j]))}")
                # Check target data
                target_data = np.load('/tmp/target_data.npy').astype(np.float64)
                print(f"  Target NaN count: {np.sum(np.isnan(target_data[:, i, j]))}")
                break
    else:
        continue
    break
