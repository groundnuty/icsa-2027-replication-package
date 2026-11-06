
import numpy as np
import pickle
import datetime

# Load saved data
baseline_sst = np.load('work/baseline_sst.npy')
with open('work/baseline_dates.pkl', 'rb') as f:
    baseline_dates = pickle.load(f)
with open('work/date_to_idx.pkl', 'rb') as f:
    date_to_idx = pickle.load(f)
with open('work/doy_to_pool_dates.pkl', 'rb') as f:
    doy_to_pool_dates = pickle.load(f)

print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Baseline dates count: {len(baseline_dates)}")

# Reconstruct doy_to_pool_dates as sets
doy_to_pool_dates = {k: set(v) for k, v in doy_to_pool_dates.items()}

# Flatten cells
n_lat, n_lon = baseline_sst.shape[1], baseline_sst.shape[2]
n_cells = n_lat * n_lon
baseline_flat = baseline_sst.reshape(len(baseline_dates), n_cells)

print(f"Flattened: {baseline_flat.shape}")

# Compute per-doy thresholds and climatology
# For each doy d (1-366, excluding 60), pool all values from pool dates
print("Computing thresholds and climatology...")
start = datetime.datetime.now()

threshold = np.full((366, n_cells), np.nan, dtype=np.float64)
climatology = np.full((366, n_cells), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    pool_dates = doy_to_pool_dates[d]
    pool_idx = [date_to_idx[date] for date in pool_dates]
    pool_data = baseline_flat[pool_idx, :]  # (n_pool, n_cells)
    
    # Compute for all cells at once
    for c in range(n_cells):
        col = pool_data[:, c]
        valid = col[~np.isnan(col)]
        if len(valid) > 0:
            threshold[d-1, c] = np.percentile(valid, 90, method='hazen')
            climatology[d-1, c] = np.mean(valid)
    
    if d % 50 == 0:
        print(f"  Processed doy {d}")

elapsed = (datetime.datetime.now() - start).total_seconds()
print(f"Done computing in {elapsed:.1f}s")

# Set day 60 (index 59) = mean of days 59 and 61 (indices 58 and 60)
threshold[59, :] = (threshold[58, :] + threshold[60, :]) / 2
climatology[59, :] = (climatology[58, :] + climatology[60, :]) / 2

# Check for NaN
print(f"Threshold NaN count: {np.isnan(threshold).sum()}")
print(f"Climatology NaN count: {np.isnan(climatology).sum()}")

# Save
np.save('work/threshold.npy', threshold)
np.save('work/climatology.npy', climatology)
print("Saved threshold and climatology")
