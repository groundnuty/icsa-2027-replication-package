
import numpy as np
import pandas as pd
import pickle

# Load data
baseline_data = np.load('/tmp/baseline_data.npy')
baseline_times = pd.DatetimeIndex(np.load('/tmp/baseline_times.npy').astype('datetime64[ns]'))

with open('/tmp/pool_indices.pkl', 'rb') as f:
    pool_indices_by_doy = pickle.load(f)

target_data = np.load('/tmp/target_data.npy')
sea_mask = np.all(~np.isnan(target_data), axis=0)

n_lat, n_lon = sea_mask.shape

# Initialize arrays with index 0-365 for doy 1-366
threshold_raw = np.full((n_lat, n_lon, 366), np.nan)  # index d-1 = doy d
clim_raw = np.full((n_lat, n_lon, 366), np.nan)

# Compute for all doy except 60
for doy in range(1, 367):
    if doy == 60:
        continue
    idx = doy - 1  # 0-based index
    pool_idx = pool_indices_by_doy[doy]
    n_pool = len(pool_idx)
    pool_flat = baseline_data[pool_idx].reshape(n_pool, -1)
    
    q90 = np.nanpercentile(pool_flat, 90, axis=0, method='hazen')
    mean_val = np.nanmean(pool_flat, axis=0)
    
    threshold_raw[:, :, idx] = q90.reshape(n_lat, n_lon)
    clim_raw[:, :, idx] = mean_val.reshape(n_lat, n_lon)

# Set day 60 (index 59) as mean of days 59 (index 58) and 61 (index 60)
threshold_raw[:, :, 59] = (threshold_raw[:, :, 58] + threshold_raw[:, :, 60]) / 2.0
clim_raw[:, :, 59] = (clim_raw[:, :, 58] + clim_raw[:, :, 60]) / 2.0

print("Threshold shape:", threshold_raw.shape)
print("Clim shape:", clim_raw.shape)

# Check for NaN in sea cells
sea_flat = sea_mask.flatten()
for doy in range(366):
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_mask[i, j] and np.isnan(threshold_raw[i, j, doy]):
                print(f"NaN threshold at ({i},{j}) doy {doy+1}")
                raise SystemExit(1)
print("No NaN in thresholds for sea cells")

# Smooth with 31-day centered moving mean wrapping around
def smooth_31(arrays):
    """Smooth a (..., 366) array with 31-day centered moving mean wrapping around."""
    result = np.zeros_like(arrays)
    for d in range(366):
        indices = [(d + offset) % 366 for offset in range(-15, 16)]
        result[..., d] = np.nanmean(arrays[..., indices], axis=-1)
    return result

threshold_smooth = smooth_31(threshold_raw)
clim_smooth = smooth_31(clim_raw)

print("Smoothed threshold shape:", threshold_smooth.shape)
print("Smoothed clim shape:", clim_smooth.shape)

# Save
np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/clim_smooth.npy', clim_smooth)
np.save('/tmp/sea_mask.npy', sea_mask)
print("Saved threshold and climatology")
