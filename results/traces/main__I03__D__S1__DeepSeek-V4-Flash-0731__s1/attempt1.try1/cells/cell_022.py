
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

# ============================================================
# Compute threshold and climatology for each sea cell and day of year
# ============================================================
# For efficiency, only compute for sea cells
sea_cell_indices = np.where(sea_cells)
n_sea = len(sea_cell_indices[0])
print(f"Number of sea cells: {n_sea}")

# Initialize arrays (366, n_lat, n_lon) for threshold and climatology
threshold = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

# For each day of year (except 60), compute pool and statistics
for doy in range(1, 367):
    if doy == 60:
        continue
    idxs = doy_to_indices[doy]
    if not idxs:
        continue
    # Extract pool for all cells
    pool = baseline_sst[idxs]  # shape: (n_pool, n_lat, n_lon)
    
    # For each sea cell, compute threshold and climatology
    for k in range(n_sea):
        i, j = sea_cell_indices[0][k], sea_cell_indices[1][k]
        values = pool[:, i, j]
        valid = np.isfinite(values)
        if np.sum(valid) == 0:
            continue
        vals = values[valid]
        # Threshold: 90th percentile (numpy method="hazen")
        thr = np.percentile(vals, 90, method='hazen')
        clim = np.mean(vals)
        threshold[doy, i, j] = thr
        climatology[doy, i, j] = clim

print("Computed thresholds and climatology for all days except day 60")

# Day 60: set to mean of days 59 and 61
threshold[60] = (threshold[59] + threshold[61]) / 2.0
climatology[60] = (climatology[59] + climatology[61]) / 2.0

# Check some values
print(f"\nSample threshold for doy=153, cell (0,0): {threshold[153, 0, 0]}")
print(f"Sample climatology for doy=153, cell (0,0): {climatology[153, 0, 0]}")
print(f"Day 60 threshold at cell (0,0): {threshold[60, 0, 0]}")
print(f"Day 59 threshold at cell (0,0): {threshold[59, 0, 0]}")
print(f"Day 61 threshold at cell (0,0): {threshold[61, 0, 0]}")

# Save
np.save('/work/threshold_raw.npy', threshold)
np.save('/work/climatology_raw.npy', climatology)
