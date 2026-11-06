
import numpy as np
import pandas as pd
import json

# ============================================
# Load data
# ============================================
baseline_data = np.load('/tmp/baseline_data.npy').astype(np.float64)
target_data = np.load('/tmp/target_data.npy').astype(np.float64)
baseline_times = np.load('/tmp/baseline_times.npy').astype('datetime64[D]')
target_times = np.load('/tmp/target_times.npy').astype('datetime64[D]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

print("baseline shape:", baseline_data.shape)
print("target shape:", target_data.shape)
print("baseline times:", baseline_times[0], "to", baseline_times[-1])
print("target times:", target_times[0], "to", target_times[-1])

# ============================================
# Step 1: Sea cells
# ============================================
# Sea cells: SST is finite on every target day
sea_mask = ~np.any(np.isnan(target_data), axis=0)
n_lat, n_lon = sea_mask.shape
n_time_t = target_data.shape[0]
print("Sea cells:", sea_mask.sum(), "of", sea_mask.size)

# ============================================
# Step 2: Day of year mapping
# ============================================
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

# Map baseline times to indices
time_index_map = {}
for i, t in enumerate(baseline_times):
    time_index_map[t] = i

# Target day of year for each target date
target_doy = np.array([day_of_year(pd.Timestamp(t).month, pd.Timestamp(t).day) for t in target_times])
print("Target doy:", target_doy[0], "to", target_doy[-1])

# ============================================
# Step 3: Pool construction for each day of year
# ============================================
pool_indices = {}
month_days_const = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

for d in range(1, 367):
    if d == 60:
        continue
    indices = set()
    for year in range(1992, 2003):
        # Convert doy d to month/day
        remaining = d
        month = 0
        while remaining > month_days_const[month]:
            remaining -= month_days_const[month]
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

print("Pool sizes:", {d: len(pool_indices[d]) for d in [1, 59, 61, 100, 200, 366]})

# ============================================
# Step 4: Compute threshold and climatology
# ============================================
n_doy = 366
threshold = np.full((n_doy, n_lat, n_lon), np.nan)
climatology = np.full((n_doy, n_lat, n_lon), np.nan)

# Get sea cell indices
sea_ij = np.where(sea_mask)
sea_pairs = list(zip(sea_ij[0], sea_ij[1]))
print("Number of sea cell pairs:", len(sea_pairs))

# Compute for each day of year (except 60)
for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    pool_data = baseline_data[idx, :, :]
    
    for i, j in sea_pairs:
        vals = pool_data[:, i, j]
        # vals should have no NaN for sea cells, but be safe
        vals = vals[~np.isnan(vals)]
        if len(vals) > 0:
            threshold[d-1, i, j] = np.quantile(vals, 0.9, method='hazen')
            climatology[d-1, i, j] = np.mean(vals)

# Day 60: mean of days 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2

print("Threshold NaN count for sea cells:", np.sum(np.isnan(threshold[:, sea_mask])))
print("Climatology NaN count for sea cells:", np.sum(np.isnan(climatology[:, sea_mask])))
