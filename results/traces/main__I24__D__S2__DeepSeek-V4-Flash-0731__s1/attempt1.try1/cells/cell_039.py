
import numpy as np
import pandas as pd

# Load data
baseline_sst = np.load('/work/baseline_sst.npy')
baseline_time = np.load('/work/baseline_time.npy', allow_pickle=True)
bt = pd.to_datetime(baseline_time)

# Load pool for a specific doy
pool_doy = np.load('/work/pool_153.npy')

# Get the pool data for a specific sea cell
# Let's find a sea cell first
target_sst = np.load('/work/target_sst.npy')
sea_cells = np.all(np.isfinite(target_sst), axis=0)

# Find first sea cell
lat_i, lon_i = np.where(sea_cells)[0][0], np.where(sea_cells)[1][0]
print(f"Sea cell at ({lat_i}, {lon_i})")

# Get pool data for this cell
pool_data = baseline_sst[pool_doy, lat_i, lon_i]
print(f"Pool data for doy 153 at cell ({lat_i}, {lon_i}):")
print(f"  Count: {len(pool_data)}")
print(f"  Finite: {np.sum(np.isfinite(pool_data))}")
print(f"  Mean: {np.nanmean(pool_data):.4f}")
print(f"  Min: {np.nanmin(pool_data):.4f}")
print(f"  Max: {np.nanmax(pool_data):.4f}")

# Compute threshold manually using hazen (type 5)
sorted_data = np.sort(pool_data[~np.isnan(pool_data)])
n = len(sorted_data)
p = 0.9
h = n * p + 0.5
pos = h - 1
j = int(np.floor(pos))
gamma = pos - j
j0 = max(0, min(j, n-1))
j1 = max(0, min(j+1, n-1))
threshold_manual = (1-gamma)*sorted_data[j0] + gamma*sorted_data[j1]
print(f"\nManual hazen threshold: {threshold_manual:.6f}")

# Compute with numpy
threshold_np = np.nanquantile(pool_data, 0.9, method='hazen')
print(f"Numpy hazen threshold: {threshold_np:.6f}")

# Compare with the stored threshold
threshold_smooth = np.load('/work/threshold_smooth.npy')
print(f"Stored smoothed threshold (doy 153): {threshold_smooth[152, lat_i, lon_i]:.6f}")
print(f"Stored raw threshold (doy 153): {np.load('/work/threshold_raw.npy')[152, lat_i, lon_i]:.6f}")

# Check climatology
clim_manual = np.nanmean(pool_data)
clim_np = np.nanmean(pool_data)
clim_smooth = np.load('/work/climatology_smooth.npy')
print(f"\nClimatology manual: {clim_manual:.6f}")
print(f"Stored smoothed climatology (doy 153): {clim_smooth[152, lat_i, lon_i]:.6f}")
print(f"Stored raw climatology (doy 153): {np.load('/work/climatology_raw.npy')[152, lat_i, lon_i]:.6f}")
