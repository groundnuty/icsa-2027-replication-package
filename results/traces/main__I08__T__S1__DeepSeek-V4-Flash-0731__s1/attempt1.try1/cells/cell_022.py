
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')  # (367, 60, 60)
climatology_raw = np.load('/tmp/climatology_raw.npy')

# Smooth with 31-day centred moving average that wraps around
def smooth_366(arr):
    """arr is (367, ...) with indices 1-366 (index 0 unused).
    Returns smoothed (367, ...). Day d averages days d-15 to d+15 (mod 366).
    """
    n = arr.shape[0] - 1  # 366
    result = np.full_like(arr, np.nan)
    for d in range(1, n+1):
        # Days d-15 to d+15, counted modulo 366 (using 1-366 indexing)
        indices = []
        for offset in range(-15, 16):
            day = ((d - 1 + offset) % n) + 1  # 1-based modulo
            indices.append(day)
        result[d] = np.nanmean(arr[indices], axis=0)
    return result

print("Smoothing threshold...")
threshold_smooth = smooth_366(threshold_raw)
print("Smoothing climatology...")
climatology_smooth = smooth_366(climatology_raw)

print("Threshold smoothed shape:", threshold_smooth.shape)
print("Climatology smoothed shape:", climatology_smooth.shape)

# Check some values
print("Threshold day 153:", threshold_smooth[153, 0, 0])
print("Threshold day 200:", threshold_smooth[200, 0, 0])
print("Climatology day 153:", climatology_smooth[153, 0, 0])

np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed arrays.")
