
import numpy as np

# Load threshold and clim
threshold = np.load('threshold.npy')
clim = np.load('clim.npy')

# Smooth with 31-day centred moving mean wrapping around
def smooth_31(arr):
    """Smooth a 366-element array with unweighted centred 31-day moving mean wrapping around."""
    # arr shape: (366,) or (366, ...)
    n = 366
    window = 31
    half = 15
    
    # Pad the array at both ends
    if arr.ndim == 1:
        padded = np.concatenate([arr[-half:], arr, arr[:half]])
    else:
        padded = np.concatenate([arr[-half:], arr, arr[:half]], axis=0)
    
    # Compute moving mean
    result = np.zeros_like(arr)
    for i in range(n):
        result[i] = np.mean(padded[i:i+window], axis=0)
    
    return result

# Apply smoothing to each cell
import time
start = time.time()

threshold_smooth = np.zeros_like(threshold)
clim_smooth = np.zeros_like(clim)

for i in range(60):
    for j in range(60):
        threshold_smooth[:, i, j] = smooth_31(threshold[:, i, j])
        clim_smooth[:, i, j] = smooth_31(clim[:, i, j])

elapsed = time.time() - start
print(f"Smoothed in {elapsed:.2f} seconds")

# Check: for sea cells, should be finite everywhere
sea_cells = np.load('sea_cells.npy')
print(f"NaN in smoothed threshold at sea cells: {np.isnan(threshold_smooth[:, sea_cells]).sum()}")
print(f"NaN in smoothed clim at sea cells: {np.isnan(clim_smooth[:, sea_cells]).sum()}")

np.save('threshold_smooth.npy', threshold_smooth)
np.save('clim_smooth.npy', clim_smooth)
print("Saved smoothed data")
