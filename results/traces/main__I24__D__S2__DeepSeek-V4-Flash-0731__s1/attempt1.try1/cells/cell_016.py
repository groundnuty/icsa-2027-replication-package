
import numpy as np
import pandas as pd
import time

# Load data
baseline_sst = np.load('/work/baseline_sst.npy')
baseline_time = np.load('/work/baseline_time.npy', allow_pickle=True)
target_sst = np.load('/work/target_sst.npy')
target_time = np.load('/work/target_time.npy', allow_pickle=True)

bt = pd.to_datetime(baseline_time)
n_baseline, n_lat, n_lon = baseline_sst.shape

# Identify sea cells
sea_cells = np.all(np.isfinite(target_sst), axis=0)
n_sea = sea_cells.sum()
print(f"Sea cells: {n_sea}")

# Load pools
pool_doys = np.load('/work/pools_keys.npy')
pools = {}
for d in pool_doys:
    pools[int(d)] = np.load(f'/work/pool_{int(d)}.npy')

print(f"Loaded {len(pools)} pools")

# Compute raw threshold and climatology for each sea cell and doy
# threshold_raw[doy, lat, lon], climatology_raw[doy, lat, lon]
# Only for sea cells; others set to NaN (they'll be 0 in output anyway)

threshold_raw = np.full((366, n_lat, n_lon), np.nan)
climatology_raw = np.full((366, n_lat, n_lon), np.nan)

print("Computing thresholds and climatologies...")
start = time.time()

for d in range(1, 367):
    if d == 60:
        continue
    mask = pools[d]
    pool_data = baseline_sst[mask]  # (n_pool, n_lat, n_lon)
    
    # For sea cells only
    # Compute per-cell percentile and mean
    # pool_data[:, sea_cells] gives (n_pool, n_sea)
    sea_data = pool_data[:, sea_cells]
    
    # Threshold (90th percentile, hazen, ignoring NaN)
    thresh = np.nanquantile(sea_data, 0.9, axis=0, method='hazen')
    # Climatology (mean, ignoring NaN)
    clim = np.nanmean(sea_data, axis=0)
    
    # Store
    threshold_raw[d, sea_cells] = thresh
    climatology_raw[d, sea_cells] = clim

# Set day 60 to mean of days 59 and 61
threshold_raw[60, sea_cells] = (threshold_raw[59, sea_cells] + threshold_raw[61, sea_cells]) / 2
climatology_raw[60, sea_cells] = (climatology_raw[59, sea_cells] + climatology_raw[61, sea_cells]) / 2

print(f"Threshold/climatology computation took {time.time()-start:.2f}s")

# Check for NaN in sea cells
for d in range(1, 367):
    assert not np.any(np.isnan(threshold_raw[d, sea_cells])), f"NaN threshold at doy {d}"
    assert not np.any(np.isnan(climatology_raw[d, sea_cells])), f"NaN climatology at doy {d}"

print("No NaN in threshold/climatology for sea cells")
print("threshold_raw[59, :5, :5] =", threshold_raw[59, :3, :3])
print("threshold_raw[60, :3, :3] =", threshold_raw[60, :3, :3])
print("threshold_raw[61, :3, :3] =", threshold_raw[61, :3, :3])

# Save raw threshold and climatology
np.save('/work/threshold_raw.npy', threshold_raw)
np.save('/work/climatology_raw.npy', climatology_raw)
print("Saved raw threshold and climatology")
