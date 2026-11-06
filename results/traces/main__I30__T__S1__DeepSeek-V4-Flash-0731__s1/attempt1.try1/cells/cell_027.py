
import numpy as np
import pandas as pd

baseline_data = np.load('/tmp/baseline_data.npy').astype(np.float64)
baseline_times = np.load('/tmp/baseline_times.npy').astype('datetime64[D]')
sea_mask = np.load('/tmp/sea_mask.npy')

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

pool_idx = sorted(indices)
pool_data = baseline_data[pool_idx, :, :]

n_lat, n_lon = sea_mask.shape

# Find cells with NaN in pool
nan_in_pool = np.any(np.isnan(pool_data), axis=0)
print("Cells with NaN in pool for day 200:", nan_in_pool.sum())

# Check if these are sea cells
print("NaN in pool AND sea cell:", np.sum(nan_in_pool & sea_mask))
print("NaN in pool AND NOT sea cell:", np.sum(nan_in_pool & ~sea_mask))

# Check which cells have NaN in the pool but ARE sea cells
problem_cells = np.where(nan_in_pool & sea_mask)
print("Problem cells (sea but NaN pool):", len(problem_cells[0]))
for k in range(min(5, len(problem_cells[0]))):
    i, j = problem_cells[0][k], problem_cells[1][k]
    print(f"  Cell ({i},{j}): NaN in pool for day {d}")
    print(f"    Sea mask: {sea_mask[i,j]}")
    # Check baseline data for this cell
    vals = baseline_data[:, i, j]
    print(f"    Baseline NaN count: {np.sum(np.isnan(vals))}")
