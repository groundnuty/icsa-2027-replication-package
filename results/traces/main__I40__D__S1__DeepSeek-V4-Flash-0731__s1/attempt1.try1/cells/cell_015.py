
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load the data
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')
base_times = np.load('/work/base_times.npy')
targ_times = np.load('/work/targ_times.npy')

base_dates = pd.DatetimeIndex(base_times)
targ_dates = pd.DatetimeIndex(targ_times)

# Day of year mapping
def date_to_doy(dt):
    """Map a datetime to day of year 1-366 as specified."""
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

# Compute doy for each baseline date
base_doy = np.array([date_to_doy(d) for d in base_dates])
targ_doy = np.array([date_to_doy(d) for d in targ_dates])

# Identify baseline dates in 1992-2002
base_mask_1992_2002 = (base_dates >= pd.Timestamp('1992-01-01')) & (base_dates <= pd.Timestamp('2002-12-31'))

# Build pools: for each doy d, list of indices in base_dates
pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    mask = base_mask_1992_2002 & (base_doy == d)
    baseline_dates_with_doy = base_dates[mask]
    pool_mask = np.zeros(len(base_dates), dtype=bool)
    for bd in baseline_dates_with_doy:
        start = bd - pd.Timedelta(days=5)
        end = bd + pd.Timedelta(days=5)
        pool_mask |= (base_dates >= start) & (base_dates <= end)
    pools[d] = np.where(pool_mask)[0]

# Now compute thresholds and climatology per cell per doy
n_cells = baseline_sst.shape[1] * baseline_sst.shape[2]
print(f"Number of cells: {n_cells}")

# Initialize arrays
thresholds = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan, dtype=np.float64)
climatology = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan, dtype=np.float64)

# For each doy, compute percentile and mean for each cell
for d in range(1, 367):
    if d == 60:
        continue
    pool_idx = pools[d]
    if len(pool_idx) == 0:
        continue
    
    # Get the pool data: (n_dates, n_cells)
    pool_data = baseline_sst[pool_idx].astype(np.float64)  # shape: (n_pool, n_lat, n_lon)
    
    # Reshape to (n_pool, n_cells)
    n_pool = len(pool_idx)
    n_lat, n_lon = baseline_sst.shape[1], baseline_sst.shape[2]
    pool_flat = pool_data.reshape(n_pool, n_lat * n_lon)
    
    # Compute 90th percentile (Hazen method) ignoring NaN, per cell
    # and mean ignoring NaN, per cell
    for c in range(n_lat * n_lon):
        vals = pool_flat[:, c]
        vals_valid = vals[~np.isnan(vals)]
        if len(vals_valid) > 0:
            thresholds[d, c // n_lon, c % n_lon] = np.quantile(vals_valid, 0.9, method='hazen')
            climatology[d, c // n_lon, c % n_lon] = np.mean(vals_valid)

# Set day 60 to mean of days 59 and 61
for lat_i in range(baseline_sst.shape[1]):
    for lon_i in range(baseline_sst.shape[2]):
        # Day 59 and 61 might have NaN if no valid data
        v59 = climatology[58, lat_i, lon_i]
        v61 = climatology[60, lat_i, lon_i]
        t59 = thresholds[58, lat_i, lon_i]
        t61 = thresholds[60, lat_i, lon_i]
        
        if not np.isnan(v59) and not np.isnan(v61):
            climatology[59, lat_i, lon_i] = (v59 + v61) / 2.0
        elif not np.isnan(v59):
            climatology[59, lat_i, lon_i] = v59
        elif not np.isnan(v61):
            climatology[59, lat_i, lon_i] = v61
            
        if not np.isnan(t59) and not np.isnan(t61):
            thresholds[59, lat_i, lon_i] = (t59 + t61) / 2.0
        elif not np.isnan(t59):
            thresholds[59, lat_i, lon_i] = t59
        elif not np.isnan(t61):
            thresholds[59, lat_i, lon_i] = t61

print("Computed thresholds and climatology")
print(f"Threshold NaN count: {np.isnan(thresholds).sum()}")
print(f"Climatology NaN count: {np.isnan(climatology).sum()}")

# Smooth with 31-day centered moving mean that wraps around
def smooth_wrap(arr):
    """Smooth a 366-element array with 31-day centered moving mean, wrapping around."""
    result = np.full_like(arr, np.nan)
    for d in range(366):
        vals = []
        for offset in range(-15, 16):
            idx = (d + offset) % 366
            if not np.isnan(arr[idx]):
                vals.append(arr[idx])
        if len(vals) > 0:
            result[d] = np.mean(vals)
    return result

# Apply smoothing per cell
for lat_i in range(baseline_sst.shape[1]):
    for lon_i in range(baseline_sst.shape[2]):
        thresholds[:, lat_i, lon_i] = smooth_wrap(thresholds[:, lat_i, lon_i])
        climatology[:, lat_i, lon_i] = smooth_wrap(climatology[:, lat_i, lon_i])

print("Smoothed thresholds and climatology")

# Save results
np.save('/work/thresholds.npy', thresholds)
np.save('/work/climatology.npy', climatology)

# Check for remaining NaN
print(f"Threshold NaN count after smoothing: {np.isnan(thresholds).sum()}")
print(f"Climatology NaN count after smoothing: {np.isnan(climatology).sum()}")

# Check some values
print(f"\nThreshold sample at doy 153 (Jun 1), cell 0,0: {thresholds[152, 0, 0]}")
print(f"Climatology sample at doy 153 (Jun 1), cell 0,0: {climatology[152, 0, 0]}")
