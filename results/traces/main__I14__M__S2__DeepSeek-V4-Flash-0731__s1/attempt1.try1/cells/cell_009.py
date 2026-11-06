
import numpy as np

# Load thresholds and climatology
thresholds = np.load('/tmp/thresholds.npy')  # (366, 60, 60)
climatology = np.load('/tmp/climatology.npy')

def smooth_366(arr):
    """Smooth a 366-element array (last axis) with a 31-day centred moving mean wrapping around."""
    # arr shape: (366, ...) or just (366,)
    # For each day d, average days d-15 to d+15 (mod 366)
    n = 366
    half = 15
    if arr.ndim == 1:
        result = np.zeros(n)
        for d in range(n):
            idx = [(d + i) % n for i in range(-half, half + 1)]
            result[d] = np.nanmean(arr[idx])
        return result
    else:
        # arr shape: (366, n_lat, n_lon)
        shape = arr.shape
        result = np.zeros_like(arr)
        for d in range(n):
            idx = [(d + i) % n for i in range(-half, half + 1)]
            result[d] = np.nanmean(arr[idx], axis=0)
        return result

# Smooth thresholds
thresholds_smoothed = smooth_366(thresholds)
climatology_smoothed = smooth_366(climatology)

print("Threshold smoothed. Sample:", thresholds_smoothed[152, 0, 0])
print("Climatology smoothed. Sample:", climatology_smoothed[152, 0, 0])

# Check for NaN
print("NaN in smoothed thresholds:", np.isnan(thresholds_smoothed).sum())
print("NaN in smoothed climatology:", np.isnan(climatology_smoothed).sum())

# Save
np.save('/tmp/thresholds_smoothed.npy', thresholds_smoothed)
np.save('/tmp/climatology_smoothed.npy', climatology_smoothed)
print("Saved smoothed arrays")
