
import numpy as np
import pandas as pd
import pickle

# Load data
baseline_data = np.load('/tmp/baseline_data.npy')
with open('/tmp/pool_indices.pkl', 'rb') as f:
    pool_indices_by_doy = pickle.load(f)

threshold_smooth = np.load('/tmp/threshold_smooth.npy')

# Verify for cell (30, 30), doy 153 (June 1)
cell_lat, cell_lon = 30, 30
doy = 153
idx = doy - 1

# Get pool values
pool_idx = pool_indices_by_doy[doy]
pool_values = baseline_data[pool_idx, cell_lat, cell_lon]
print(f"Cell ({cell_lat}, {cell_lon}), DOY {doy}:")
print(f"  Pool size: {len(pool_values)}")
print(f"  Pool values: {pool_values}")

# Compute 90th percentile with method='hazen'
q90 = np.nanpercentile(pool_values, 90, method='hazen')
mean_val = np.nanmean(pool_values)
print(f"  Manual 90th percentile (hazen): {q90}")
print(f"  Manual mean: {mean_val}")
print(f"  Computed threshold (raw): {threshold_smooth[cell_lat, cell_lon, idx] if False else 'see below'}")

# The threshold stored is smoothed, so let me verify the raw threshold first
# Actually, we already computed the raw threshold in the main script
# Let me check that the percentile and mean computations are correct

# Verify with numpy's hazen method explicitly
q90_check = np.percentile(pool_values, 90, method='hazen')
print(f"  np.percentile hazen: {q90_check}")
print(f"  Match: {q90 == q90_check}")

# Verify with scipy
try:
    from scipy import stats
    q90_scipy = stats.scoreatpercentile(pool_values, 90, interpolation_method='hazen')
    print(f"  scipy scoreatpercentile: {q90_scipy}")
except:
    pass

# Now verify the smoothing for this cell
# Load raw threshold
threshold_raw = np.full((60, 60, 366), np.nan)
for d in range(1, 367):
    if d == 60:
        continue
    pool_idx_d = pool_indices_by_doy[d]
    pool_flat = baseline_data[pool_idx_d].reshape(len(pool_idx_d), -1)
    q90_d = np.nanpercentile(pool_flat, 90, axis=0, method='hazen')
    threshold_raw[:, :, d-1] = q90_d.reshape(60, 60)

# Day 60
threshold_raw[:, :, 59] = (threshold_raw[:, :, 58] + threshold_raw[:, :, 60]) / 2.0

# Compute smoothed value for doy 153
d_idx = 152  # 0-based index for doy 153
indices = [(d_idx + offset) % 366 for offset in range(-15, 16)]
smoothed_manual = np.nanmean(threshold_raw[cell_lat, cell_lon, indices])
print(f"\n  Smoothed threshold for DOY 153: {smoothed_manual}")
print(f"  From saved array: {threshold_smooth[cell_lat, cell_lon, d_idx]}")
print(f"  Match: {abs(smoothed_manual - threshold_smooth[cell_lat, cell_lon, d_idx]) < 1e-12}")
