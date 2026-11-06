
import numpy as np
import pandas as pd
import pickle

# Load data
sst_baseline = np.load('/tmp/sst_baseline.npy').astype(np.float64)  # (4028, 60, 60)
sea_cells = np.load('/tmp/sea_cells.npy')  # (60, 60)
baseline_dates = np.load('/tmp/baseline_dates.npy')

with open('/tmp/pool_indices.pkl', 'rb') as f:
    pool_indices = pickle.load(f)

print("sst_baseline dtype:", sst_baseline.dtype, "shape:", sst_baseline.shape)
n_lat, n_lon = 60, 60

# Precompute for each doy the threshold and climatology arrays
# threshold[d] shape (60, 60), climatology[d] shape (60, 60)
n_doy = 366
threshold_raw = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
clim_raw = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    if len(idx) == 0:
        continue
    # Extract SST values for all cells
    pool_data = sst_baseline[idx, :, :]  # (n_pool, 60, 60)
    
    # Compute threshold (90th percentile) and climatology (mean) for each cell
    # Use nanpercentile with method='hazen' and nanmean
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool_data[:, i, j]
            if np.all(np.isnan(vals)):
                continue
            threshold_raw[d, i, j] = np.nanpercentile(vals, 90, method='hazen')
            clim_raw[d, i, j] = np.nanmean(vals)

print("Threshold computation done")
print("Example: day 153, lat 50, lon 360:", threshold_raw[153, 50, 360], clim_raw[153, 50, 360])

# Save raw threshold and climatology
np.save('/tmp/threshold_raw.npy', threshold_raw)
np.save('/tmp/clim_raw.npy', clim_raw)
print("Saved raw threshold and climatology")
