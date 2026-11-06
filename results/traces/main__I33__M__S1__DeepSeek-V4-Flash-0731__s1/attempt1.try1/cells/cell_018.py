
import numpy as np
import pickle
import time

# Load pool values
with open('output/pool_values.pkl', 'rb') as f:
    pool_values = pickle.load(f)

print(f"Days of year with pools: {len(pool_values)}")

n_lat = 60
n_lon = 60

# Initialize arrays
threshold_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

start_time = time.time()
for d_doy in pool_values:
    if d_doy == 60:
        continue
    
    # Stack all values: (n_dates, n_lat, n_lon)
    stack = np.array(pool_values[d_doy], dtype=np.float64)
    
    # Compute threshold: 90th percentile using Hazen method, ignoring NaN
    threshold_raw[d_doy-1] = np.nanquantile(stack, 0.9, axis=0, method='hazen')
    
    # Compute climatology: mean, ignoring NaN
    climatology_raw[d_doy-1] = np.nanmean(stack, axis=0)

elapsed = time.time() - start_time
print(f"Computed thresholds and climatology in {elapsed:.1f} seconds")

# Check values
print(f"Threshold day 1, cell [30,30]: {threshold_raw[0, 30, 30]:.4f}")
print(f"Clim day 1, cell [30,30]: {climatology_raw[0, 30, 30]:.4f}")
print(f"Threshold day 153, cell [30,30]: {threshold_raw[152, 30, 30]:.4f}")
print(f"Clim day 153, cell [30,30]: {climatology_raw[152, 30, 30]:.4f}")

# Check for any days where threshold is NaN for all cells
for d in range(366):
    if d != 59:  # Skip day 60 (index 59)
        if np.isnan(threshold_raw[d]).all():
            print(f"Day {d+1}: all NaN threshold")

# Check specific cells for NaN
nan_cells = np.isnan(threshold_raw[0])
print(f"Day 1: {nan_cells.sum()} NaN cells out of {60*60}")

# Save intermediate results
np.save('output/threshold_raw.npy', threshold_raw)
np.save('output/climatology_raw.npy', climatology_raw)
print("Saved intermediate results")
