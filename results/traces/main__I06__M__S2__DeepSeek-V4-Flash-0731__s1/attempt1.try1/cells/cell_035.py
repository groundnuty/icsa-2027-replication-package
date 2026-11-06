
import numpy as np
import pandas as pd
import pickle

# Load data
sst_baseline = np.load('/tmp/sst_baseline.npy').astype(np.float64)
sea_cells = np.load('/tmp/sea_cells.npy')
baseline_dates = np.load('/tmp/baseline_dates.npy')

with open('/tmp/pool_indices.pkl', 'rb') as f:
    pool_indices = pickle.load(f)

# Verify threshold for a specific cell and doy
# Find a sea cell
sea_idx = np.where(sea_cells)
i, j = sea_idx[0][0], sea_idx[1][0]
print(f"Cell ({i},{j})")

# Check doy 153 (Jun 1)
d = 153
idx = pool_indices[d]
print(f"Day {d}: {len(idx)} pool dates")

# Get pool values for this cell
pool_vals = sst_baseline[idx, i, j]
non_nan = pool_vals[~np.isnan(pool_vals)]
print(f"Pool values (non-NaN): {len(non_nan)}")
print(f"First few: {non_nan[:5]}")
print(f"min={non_nan.min():.4f}, max={non_nan.max():.4f}")

# Compute threshold and climatology manually
thr = np.nanpercentile(pool_vals, 90, method='hazen')
clim = np.nanmean(pool_vals)
print(f"Manual threshold: {thr:.4f}")
print(f"Manual clim: {clim:.4f}")

# Compare with stored
threshold_raw = np.load('/tmp/threshold_raw.npy')
clim_raw = np.load('/tmp/clim_raw.npy')
print(f"Stored threshold: {threshold_raw[d, i, j]:.4f}")
print(f"Stored clim: {clim_raw[d, i, j]:.4f}")

# Also verify the pool dates
baseline_dates_pd = pd.to_datetime(baseline_dates)
pool_dates = [pd.Timestamp(baseline_dates_pd[k]) for k in idx]
print(f"Pool date range: {pool_dates[0]} to {pool_dates[-1]}")
print(f"Pool dates sample (every 11th):")
for k in range(0, len(pool_dates), 11):
    print(f"  {pool_dates[k]}")
