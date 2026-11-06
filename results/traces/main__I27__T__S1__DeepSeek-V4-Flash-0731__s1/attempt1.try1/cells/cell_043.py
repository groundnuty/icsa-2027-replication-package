
import numpy as np
import pandas as pd
import pickle

# Load data
baseline_data = np.load('/tmp/baseline_data.npy')
baseline_times = pd.DatetimeIndex(np.load('/tmp/baseline_times.npy').astype('datetime64[ns]'))

with open('/tmp/pool_indices.pkl', 'rb') as f:
    pool_indices_by_doy = pickle.load(f)

# Sea cells
target_data = np.load('/tmp/target_data.npy')
sea_mask = np.all(~np.isnan(target_data), axis=0)

# Number of sea cells and grid dimensions
n_lat, n_lon = sea_mask.shape
sea_cells = np.argwhere(sea_mask)
print(f"Number of sea cells: {len(sea_cells)}")

# Compute threshold and climatology for each cell
# We'll do this cell by cell
# For efficiency, we can compute for all cells simultaneously

# Initialize arrays
threshold_raw = np.full((n_lat, n_lon, 366), np.nan)  # (lat, lon, doy)
clim_raw = np.full((n_lat, n_lon, 366), np.nan)

# Compute for all doy except 60
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_idx = pool_indices_by_doy[doy]
    # Extract pool values for all cells: (n_pool, n_lat, n_lon)
    pool_vals = baseline_data[pool_idx]  # (n_pool, n_lat, n_lon)
    
    # For each cell, compute percentile and mean ignoring NaN
    # Use nanquantile with method="hazen" and nanmean
    
    # We need to handle this efficiently. Let's use apply_along_axis or loop over cells.
    # With 3600 cells and 365 doys, we need to be efficient.
    
    # Compute for all cells at once
    # pool_vals: (n_pool, n_lat, n_lon)
    # For each (lat, lon), compute nanquantile(pool_vals[:, lat, lon], 0.9) and nanmean
    
    # Reshape to (n_pool, n_cells)
    n_pool = len(pool_idx)
    pool_flat = pool_vals.reshape(n_pool, -1)  # (n_pool, n_lat*n_lon)
    
    # Compute 90th percentile for each cell
    q90 = np.nanpercentile(pool_flat, 90, axis=0, method='hazen')
    mean_val = np.nanmean(pool_flat, axis=0)
    
    # Reshape back
    threshold_raw[:, :, doy] = q90.reshape(n_lat, n_lon)
    clim_raw[:, :, doy] = mean_val.reshape(n_lat, n_lon)

# Set day 60 as mean of days 59 and 61
threshold_raw[:, :, 60] = (threshold_raw[:, :, 59] + threshold_raw[:, :, 61]) / 2.0
clim_raw[:, :, 60] = (clim_raw[:, :, 59] + clim_raw[:, :, 61]) / 2.0

print("Threshold shape:", threshold_raw.shape)
print("Clim shape:", clim_raw.shape)

# Check some values
print("Sample threshold for cell 30,30, doy 100:", threshold_raw[30, 30, 100])
print("Sample clim for cell 30,30, doy 100:", clim_raw[30, 30, 100])

# Now smooth with 31-day centered moving mean wrapping around
def smooth_31(arrays):
    """Smooth a (..., 366) array with 31-day centered moving mean wrapping around."""
    # arrays: (..., 366)
    result = np.zeros_like(arrays)
    # For each day d, average days d-15 to d+15 (mod 366)
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
