
import numpy as np
import pandas as pd

baseline_data = np.load('/tmp/baseline_data.npy').astype(np.float64)
baseline_times = np.load('/tmp/baseline_times.npy').astype('datetime64[D]')
target_data = np.load('/tmp/target_data.npy').astype(np.float64)
sea_mask = np.load('/tmp/sea_mask.npy')

time_index_map = {}
for i, t in enumerate(baseline_times):
    time_index_map[t] = i

def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

# Build pool indices for all days (we need unsmoothed threshold)
pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
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
    
    pool_indices[d] = sorted(indices)

# Target day-of-year values
target_times = np.load('/tmp/target_times.npy').astype('datetime64[D]')
target_doy = np.array([day_of_year(pd.Timestamp(t).month, pd.Timestamp(t).day) for t in target_times])
print("Target doy range:", target_doy.min(), target_doy.max())

# Check unsmoothed threshold for target days (doy 153-244) 
# and their smoothing window (doy 138-259)
check_days = set(range(138, 260))  # inclusive

n_lat, n_lon = sea_mask.shape
n_doy = 366

# Compute unsmoothed threshold and check NaN for these days
threshold_unsmooth = np.full((n_doy, n_lat, n_lon), np.nan)

for d in check_days:
    if d == 60:
        continue
    idx = pool_indices[d]
    pool_data = baseline_data[idx, :, :]
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_mask[i, j]:
                vals = pool_data[:, i, j]
                vals = vals[~np.isnan(vals)]
                if len(vals) > 0:
                    threshold_unsmooth[d-1, i, j] = np.quantile(vals, 0.9, method='hazen')

# Check NaN in unsmoothed threshold for these days
nan_mask = np.isnan(threshold_unsmooth)
print("NaN count in unsmoothed threshold for days 138-259:", nan_mask.sum())

# Check specific days
for d in sorted(check_days):
    nan_for_day = nan_mask[d-1, :, :].sum()
    if nan_for_day > 0:
        print(f"  Day {d} (doy): {nan_for_day} NaN values")
