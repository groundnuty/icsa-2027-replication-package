
import numpy as np
import pandas as pd

baseline_data = np.load('/tmp/baseline_data.npy').astype(np.float64)
baseline_times = np.load('/tmp/baseline_times.npy').astype('datetime64[D]')

# Pool indices for each day of year (reconstructing from previous cell)
# Actually, let me save the pool_indices from the previous computation
# Let me redo it here

time_index_map = {}
for i, t in enumerate(baseline_times):
    time_index_map[t] = i

def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

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

# Now compute threshold and climatology for each sea cell and day of year
# First, determine sea cells (finite on every target day)
target_data = np.load('/tmp/target_data.npy').astype(np.float64)
sea_mask = ~np.any(np.isnan(target_data), axis=0)
print("Sea cells:", sea_mask.sum(), "of", sea_mask.size)

n_lat, n_lon = sea_mask.shape
n_doy = 366

# Initialize threshold and climatology arrays
threshold = np.full((n_doy, n_lat, n_lon), np.nan)
climatology = np.full((n_doy, n_lat, n_lon), np.nan)

# Compute for each day of year (except 60) and each sea cell
for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    pool_data = baseline_data[idx, :, :]  # shape (n_pool, n_lat, n_lon)
    
    # Compute per-cell
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_mask[i, j]:
                vals = pool_data[:, i, j]
                vals = vals[~np.isnan(vals)]
                if len(vals) > 0:
                    # Threshold: 90th percentile with method='hazen' (type 5)
                    threshold[d, i, j] = np.quantile(vals, 0.9, method='hazen')
                    climatology[d, i, j] = np.mean(vals)

print("Computed threshold and climatology")
print("Threshold non-NaN count:", np.sum(~np.isnan(threshold)))
print("Climatology non-NaN count:", np.sum(~np.isnan(climatology)))

# Day 60: mean of days 59 and 61
threshold[60, :, :] = (threshold[59, :, :] + threshold[61, :, :]) / 2
climatology[60, :, :] = (climatology[59, :, :] + climatology[61, :, :]) / 2

# Smooth with 31-day centered moving mean that wraps
def smooth_wrap(arr):
    """Smooth a 366-element array with unweighted 31-day centered moving mean that wraps."""
    result = np.zeros_like(arr)
    for d in range(366):
        total = 0
        count = 0
        for offset in range(-15, 16):
            idx = (d + offset) % 366
            if not np.isnan(arr[idx]):
                total += arr[idx]
                count += 1
        if count > 0:
            result[d] = total / count
        else:
            result[d] = np.nan
    return result

# Smooth threshold and climatology per cell
threshold_smooth = np.full_like(threshold, np.nan)
climatology_smooth = np.full_like(climatology, np.nan)

for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i, j]:
            threshold_smooth[:, i, j] = smooth_wrap(threshold[:, i, j])
            climatology_smooth[:, i, j] = smooth_wrap(climatology[:, i, j])

print("Smoothed threshold and climatology")
print("threshold_smooth non-NaN count:", np.sum(~np.isnan(threshold_smooth)))
print("climatology_smooth non-NaN count:", np.sum(~np.isnan(climatology_smooth)))

# Save results
np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/climatology_smooth.npy', climatology_smooth)
np.save('/tmp/sea_mask.npy', sea_mask)
np.save('/tmp/pool_indices.npy', pool_indices, allow_pickle=True)
print("Saved.")
