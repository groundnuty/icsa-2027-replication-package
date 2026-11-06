
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')
target_sst = np.load('/tmp/target_sst.npy')
baseline_time = np.load('/tmp/baseline_time.npy')
target_time = np.load('/tmp/target_time.npy')

# Define day-of-year mapping
def doy_from_date(dt):
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

# Convert to datetime
baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

# Find strict baseline indices (1992-01-01 to 2002-12-31)
strict_base_start = pd.Timestamp('1992-01-01')
strict_base_end = pd.Timestamp('2002-12-31')
strict_mask = [(d >= strict_base_start and d <= strict_base_end) for d in baseline_dates]
strict_idx = np.where(strict_mask)[0]

# Compute DOY for each date in the full baseline array
base_doy = np.array([doy_from_date(d) for d in baseline_dates])
print("Base DOY:", base_doy[:10], "...")

# Build mapping from strict baseline indices to their DOY
strict_doy = base_doy[strict_idx]

# Sea cells
sea_mask = ~np.isnan(target_sst).any(axis=0)
n_sea = sea_mask.sum()
print(f"Sea cells: {n_sea}")

# Convert to float64
baseline_sst64 = baseline_sst.astype(np.float64)
target_sst64 = target_sst.astype(np.float64)

# For each DOY d (1-366, except 60), build the pool indices
# For each DOY d, find all dates in the full baseline array that are within ±5 days
# of a strict baseline date with DOY d

# Precompute a date-to-index mapping for the full baseline
base_date_to_idx = {}
for i, d in enumerate(baseline_dates):
    base_date_to_idx[d] = i

print("Building pools...")

# Initialize threshold and climatology arrays
threshold = np.full((366, 60, 60), np.nan)
climatology = np.full((366, 60, 60), np.nan)

# For each day of year d (except 60)
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find strict baseline dates with this DOY
    dates_with_doy = []
    for i in strict_idx:
        if base_doy[i] == d:
            dates_with_doy.append(baseline_dates[i])
    
    if len(dates_with_doy) == 0:
        print(f"Warning: no baseline dates for DOY {d}")
        continue
    
    # For each such date, find indices of dates within ±5 days
    pool_indices = set()
    for bd in dates_with_doy:
        for offset in range(-5, 6):
            candidate = bd + timedelta(days=offset)
            if candidate in base_date_to_idx:
                pool_indices.add(base_date_to_idx[candidate])
    
    pool_indices = sorted(pool_indices)
    
    # Extract SST values for this pool for all sea cells
    pool_data = baseline_sst64[pool_indices]  # shape: (n_pool, 60, 60)
    
    # Compute threshold (90th percentile, Hazen) and climatology (mean) for each cell
    # Only for sea cells
    for lat_i in range(60):
        for lon_j in range(60):
            if sea_mask[lat_i, lon_j]:
                values = pool_data[:, lat_i, lon_j]
                # Ignore NaN
                valid = values[~np.isnan(values)]
                if len(valid) > 0:
                    threshold[d-1, lat_i, lon_j] = np.percentile(valid, 90, method='hazen')
                    climatology[d-1, lat_i, lon_j] = np.mean(valid)
    
    if d % 50 == 0:
        print(f"  Processed DOY {d}")

print("Done building pools")

# Set day 60 to mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

print("Day 60 set")

# Check for NaN in threshold/climatology for sea cells
for lat_i in range(60):
    for lon_j in range(60):
        if sea_mask[lat_i, lon_j]:
            if np.isnan(threshold[:, lat_i, lon_j]).any():
                print(f"NaN in threshold at ({lat_i}, {lon_j})")
            if np.isnan(climatology[:, lat_i, lon_j]).any():
                print(f"NaN in climatology at ({lat_i}, {lon_j})")

print("No NaNs in sea cell thresholds/climatologies")

# Save intermediate results
np.save('/tmp/threshold.npy', threshold)
np.save('/tmp/climatology.npy', climatology)
np.save('/tmp/sea_mask.npy', sea_mask)
