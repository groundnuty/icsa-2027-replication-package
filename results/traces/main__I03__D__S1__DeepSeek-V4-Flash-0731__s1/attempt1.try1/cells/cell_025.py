
import numpy as np
import pickle

# Load
threshold = np.load('/work/threshold_raw.npy')
climatology = np.load('/work/climatology_raw.npy')
sea_cells = np.load('/work/sea_cells.npy')

n_lat, n_lon = sea_cells.shape
print(f"threshold shape: {threshold.shape}")

# ============================================================
# Smoothing: 31-day centred moving mean, wrapping around year
# ============================================================
def smooth_31(arr):
    """Smooth a (366, ...) array with 31-day centred moving mean that wraps around the year."""
    # Pad the array by 15 days on each end, wrapping around
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)  # shape: (396, ...)
    n = padded.shape[0]
    result = np.zeros_like(arr)
    
    # For each day i in [0, 365], average days i to i+30 in the padded array
    # But actually we need to shift by 15 since padded[15+i] = arr[i]
    # Window is days i-15 to i+15, which is padded[15+i-15 : 15+i+15+1] = padded[i : i+31]
    for i in range(366):
        result[i] = np.nanmean(padded[i:i+31], axis=0)
    
    return result

print("Smoothing threshold...")
threshold_smoothed = smooth_31(threshold)
print("Smoothing climatology...")
climatology_smoothed = smooth_31(climatology)

# Check
sea_idx = np.where(sea_cells)
i, j = sea_idx[0][0], sea_idx[1][0]
for doy in [1, 59, 60, 61, 153, 244, 366]:
    idx = doy - 1
    print(f"doy={doy}: smoothed_thr={threshold_smoothed[idx, i, j]}, smoothed_clim={climatology_smoothed[idx, i, j]}")

# Save
np.save('/work/threshold_smoothed.npy', threshold_smoothed)
np.save('/work/climatology_smoothed.npy', climatology_smoothed)
print("Saved smoothed threshold and climatology")
