
import numpy as np
import pandas as pd
import pickle

# Load data
sst_baseline = np.load('/tmp/sst_baseline.npy').astype(np.float64)
sea_cells = np.load('/tmp/sea_cells.npy')
baseline_dates = np.load('/tmp/baseline_dates.npy')

with open('/tmp/pool_indices.pkl', 'rb') as f:
    pool_indices = pickle.load(f)

print("sst_baseline dtype:", sst_baseline.dtype, "shape:", sst_baseline.shape)
n_lat, n_lon = 60, 60

# Use 367-element array: index 0 unused, index 1 = doy 1, ..., index 366 = doy 366
n_doy = 367
threshold_raw = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
clim_raw = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    if len(idx) == 0:
        continue
    pool_data = sst_baseline[idx, :, :]
    
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool_data[:, i, j]
            if np.all(np.isnan(vals)):
                continue
            threshold_raw[d, i, j] = np.nanpercentile(vals, 90, method='hazen')
            clim_raw[d, i, j] = np.nanmean(vals)

print("Threshold computation done")
print("Example: day 153, cell (50, 30):", threshold_raw[153, 50, 30], clim_raw[153, 50, 30])

# Save
np.save('/tmp/threshold_raw.npy', threshold_raw)
np.save('/tmp/clim_raw.npy', clim_raw)
print("Saved raw threshold and climatology")
