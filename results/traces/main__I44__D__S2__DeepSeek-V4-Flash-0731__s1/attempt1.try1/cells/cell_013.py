
import numpy as np

thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')
sea_cells = np.load('/work/sea_cells.npy')

print(f"Thresholds shape: {thresholds.shape}")
print(f"Climatology shape: {climatology.shape}")

n_lat, n_lon, n_doy = thresholds.shape
assert n_doy == 366

# Smooth with 31-day centered moving mean wrapping around
# Day d (0-indexed: i) averages days i-15 through i+15 (mod 366)
def smooth_wrap(arr):
    """Smooth a (..., n_doy) array along the last axis with a 31-day centered moving mean."""
    n = arr.shape[-1]
    assert n == 366
    result = np.zeros_like(arr)
    
    for i in range(n):
        indices = [(i + offset) % n for offset in range(-15, 16)]
        result[..., i] = np.mean(arr[..., indices], axis=-1)
    
    return result

print("Smoothing thresholds...")
thresholds_smooth = smooth_wrap(thresholds)
print("Smoothing climatology...")
climatology_smooth = smooth_wrap(climatology)

np.save('/work/thresholds_smooth.npy', thresholds_smooth)
np.save('/work/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed thresholds and climatology")
print(f"Smoothed shapes: {thresholds_smooth.shape}, {climatology_smooth.shape}")
