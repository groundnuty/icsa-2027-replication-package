
import numpy as np

# Smooth thresholds and climatology with 31-day centered moving mean wrapping around
def smooth_wrap(arr):
    """arr: (366, nlat, nlon) -> smoothed (366, nlat, nlon)"""
    # Extend the array
    result = np.zeros_like(arr)
    for d in range(366):
        # Days d-15 to d+15, counted modulo 366
        indices = [(d - 15 + i) % 366 for i in range(31)]
        # Handle wrap-around for indexing
        result[d] = np.mean(arr[indices], axis=0)
    return result

print("Smoothing thresholds...")
thresholds_smooth = smooth_wrap(thresholds)
print("Smoothing climatology...")
climatology_smooth = smooth_wrap(climatology)

print("Thresholds smoothed:", thresholds_smooth.shape)
print("Climatology smoothed:", climatology_smooth.shape)
print("Example threshold[100,0,0]:", thresholds_smooth[100,0,0])
print("Example climatology[100,0,0]:", climatology_smooth[100,0,0])
