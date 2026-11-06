
import numpy as np
import pickle

# Load state
sea_cells = np.load('/work/sea_cells.npy')
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')

with open('/work/doy_to_indices.pkl', 'rb') as f:
    doy_to_indices = pickle.load(f)
with open('/work/baseline_dates_dt.pkl', 'rb') as f:
    baseline_dates_dt = pickle.load(f)
with open('/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)

n_lat, n_lon = sea_cells.shape
print(f"Grid: {n_lat} x {n_lon}, sea cells: {np.sum(sea_cells)}")

# Initialize arrays (366, n_lat, n_lon) for threshold and climatology
# index i corresponds to day of year i+1
threshold = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

sea_cell_indices = np.where(sea_cells)
n_sea = len(sea_cell_indices[0])

# For each day of year (except 60), compute pool and statistics
for doy in range(1, 367):
    if doy == 60:
        continue
    idxs = doy_to_indices[doy]
    if not idxs:
        continue
    pool = baseline_sst[idxs]  # shape: (n_pool, n_lat, n_lon)
    
    doy_idx = doy - 1  # 0-indexed
    
    for k in range(n_sea):
        i, j = sea_cell_indices[0][k], sea_cell_indices[1][k]
        values = pool[:, i, j]
        valid = np.isfinite(values)
        if np.sum(valid) == 0:
            continue
        vals = values[valid]
        thr = np.percentile(vals, 90, method='hazen')
        clim = np.mean(vals)
        threshold[doy_idx, i, j] = thr
        climatology[doy_idx, i, j] = clim

print("Computed thresholds and climatology for all days except day 60")

# Day 60: index 59 in 0-indexed array
# Set to mean of day 59 (index 58) and day 61 (index 60)
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# Check
print(f"Day 59 (idx 58) threshold at cell (0,0): {threshold[58, 0, 0]}")
print(f"Day 60 (idx 59) threshold at cell (0,0): {threshold[59, 0, 0]}")
print(f"Day 61 (idx 60) threshold at cell (0,0): {threshold[60, 0, 0]}")

# Save
np.save('/work/threshold_raw.npy', threshold)
np.save('/work/climatology_raw.npy', climatology)
print("Saved raw threshold and climatology")
