
import numpy as np
import pickle
import datetime as dt

# Load state
sea_cells = np.load('/work/sea_cells.npy')
baseline_sst = np.load('/work/baseline_sst.npy')
threshold_raw = np.load('/work/threshold_raw.npy')
climatology_raw = np.load('/work/climatology_raw.npy')
threshold_smoothed = np.load('/work/threshold_smoothed.npy')

with open('/work/doy_to_indices.pkl', 'rb') as f:
    doy_to_indices = pickle.load(f)
with open('/work/baseline_dates_dt.pkl', 'rb') as f:
    baseline_dates_dt = pickle.load(f)

# Pick a specific sea cell and day of year
sea_idx = np.where(sea_cells)
i, j = sea_idx[0][0], sea_idx[1][0]
doy = 153  # June 1

# Get pool indices for this doy
idxs = doy_to_indices[doy]
pool = baseline_sst[idxs, i, j]

# Compute threshold manually
valid = np.isfinite(pool)
print(f"Pool size: {len(pool)}, valid: {np.sum(valid)}")
print(f"Pool values (first 10): {pool[valid][:10]}")

# Manual threshold using hazen
vals = pool[valid]
thr_manual = np.percentile(vals, 90, method='hazen')
clim_manual = np.mean(vals)

# Compare with computed
thr_computed = threshold_raw[doy - 1, i, j]
clim_computed = climatology_raw[doy - 1, i, j]

print(f"Manual threshold: {thr_manual}")
print(f"Computed threshold: {thr_computed}")
print(f"Match: {np.isclose(thr_manual, thr_computed)}")
print(f"Manual climatology: {clim_manual}")
print(f"Computed climatology: {clim_computed}")
print(f"Match: {np.isclose(clim_manual, clim_computed)}")

# Verify smoothed value
# For doy=153, the window is doy 138-168 (indices 137-167 in 0-indexed)
window = threshold_raw[137:168, i, j]
smoothed_manual = np.nanmean(window)
print(f"\nManual smoothed: {smoothed_manual}")
print(f"Computed smoothed: {threshold_smoothed[doy - 1, i, j]}")
print(f"Match: {np.isclose(smoothed_manual, threshold_smoothed[doy - 1, i, j])}")
