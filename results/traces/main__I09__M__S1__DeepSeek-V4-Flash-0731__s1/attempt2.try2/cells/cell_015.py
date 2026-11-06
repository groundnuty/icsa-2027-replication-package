
import numpy as np
from datetime import date, timedelta

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Load pool indices
doy_pool_indices = np.load('/tmp/doy_pool_indices.npy', allow_pickle=True)

n_lat, n_lon = sea_cells.shape
n_cells = n_lat * n_lon

# Pre-compute thresholds and climatology for all cells and all doys (1-366)
# threshold[doy-1, lat, lon] and climatology[doy-1, lat, lon]
# doy 60 will be set later as mean of doy 59 and 61

thresholds = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    pool_idx = doy_pool_indices[d]
    pool = baseline_sst[pool_idx]  # (n_pool, n_lat, n_lon)
    
    # Compute per-cell (per (lat, lon) position)
    # For each cell, compute 90th percentile (hazen) and mean ignoring NaN
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool[:, i, j]
            vals_valid = vals[~np.isnan(vals)]
            if len(vals_valid) > 0:
                thresholds[d-1, i, j] = np.quantile(vals_valid, 0.9, method='hazen')
                climatology[d-1, i, j] = np.mean(vals_valid)
    
    if d % 50 == 0:
        print(f"Processed doy {d}")

# Set doy 60 (index 59) to mean of doys 59 and 61 (indices 58 and 60)
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Verify
print(f"Thresholds shape: {thresholds.shape}")
print(f"Climatology shape: {climatology.shape}")
print(f"Thresholds NaN count: {np.isnan(thresholds).sum()}")
print(f"Climatology NaN count: {np.isnan(climatology).sum()}")

# Check some values for a sea cell
# Find a sea cell
si, sj = np.where(sea_cells)
si, sj = si[0], sj[0]
print(f"Sea cell at ({si}, {sj}):")
print(f"  Threshold doy 180: {thresholds[179, si, sj]}")
print(f"  Climatology doy 180: {climatology[179, si, sj]}")
print(f"  Threshold doy 60: {thresholds[59, si, sj]}")
print(f"  Threshold doy 59: {thresholds[58, si, sj]}")
print(f"  Threshold doy 61: {thresholds[60, si, sj]}")

np.save('/tmp/thresholds.npy', thresholds)
np.save('/tmp/climatology.npy', climatology)
print("Thresholds and climatology saved")
