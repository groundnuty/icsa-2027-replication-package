
import numpy as np

thresholds = np.load('/work/thresholds_raw.npy')  # (367, 60, 60)
climatology = np.load('/work/climatology_raw.npy')

# Smooth each as a 366-element array (DOY 1-366) with 31-day centered moving mean
# that wraps around: day d averages days d-15 to d+15, counted modulo 366

def smooth_wrap(arr_366):
    """Smooth a 366-element array with a 31-day centered moving mean wrapping around."""
    result = np.zeros(366, dtype=np.float64)
    for d in range(366):
        # d is 0-indexed for DOY d+1
        total = 0.0
        count = 0
        for offset in range(-15, 16):
            idx = (d + offset) % 366
            val = arr_366[idx]
            if np.isfinite(val):
                total += val
                count += 1
        if count > 0:
            result[d] = total / count
        else:
            result[d] = np.nan
    return result

# Apply smoothing to each cell
n_lat, n_lon = thresholds.shape[1], thresholds.shape[2]
thresholds_smooth = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)
climatology_smooth = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)

sea_cells = np.all(np.isfinite(np.load('/work/target_sst.npy')), axis=0)
sea_indices = np.where(sea_cells)
sea_pairs = list(zip(sea_indices[0], sea_indices[1]))

print(f"Smoothing {len(sea_pairs)} sea cells...")
for idx, (lat_i, lon_i) in enumerate(sea_pairs):
    if idx % 500 == 0:
        print(f"  Processing cell {idx}/{len(sea_pairs)}...")
    
    # Extract DOY 1-366 (indices 1-366)
    thresh_366 = thresholds[1:, lat_i, lon_i]  # index 0 = DOY 1
    clim_366 = climatology[1:, lat_i, lon_i]
    
    # Check that all values are finite
    if not np.all(np.isfinite(thresh_366)):
        print(f"  WARNING: Cell ({lat_i},{lon_i}) has non-finite threshold values")
    
    # Smooth
    thresh_smooth = smooth_wrap(thresh_366)
    clim_smooth = smooth_wrap(clim_366)
    
    thresholds_smooth[1:, lat_i, lon_i] = thresh_smooth
    climatology_smooth[1:, lat_i, lon_i] = clim_smooth

print("Done smoothing.")

# Verify
missing_thresh = np.sum(np.isnan(thresholds_smooth[1:]), axis=0)
print(f"Cells with missing smoothed thresholds: {np.sum(missing_thresh > 0)}")

# Check a sea cell's smoothed values
cell_ok = np.where(np.all(np.isfinite(thresholds_smooth[1:]), axis=0))
print(f"Cells with all finite smoothed thresholds: {len(cell_ok[0])}")

np.save('/work/thresholds_smooth.npy', thresholds_smooth)
np.save('/work/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed thresholds and climatology.")
