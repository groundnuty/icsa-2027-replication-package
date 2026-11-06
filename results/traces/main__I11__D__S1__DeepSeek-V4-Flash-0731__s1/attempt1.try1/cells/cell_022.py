
import numpy as np

# Load data
thresholds = np.load('/work/thresholds.npy')  # (366, 60, 60)
climatology = np.load('/work/climatology.npy')  # (366, 60, 60)
sea_mask = np.load('/work/sea_mask.npy')

def smooth_wrap(arr, window=31):
    """Smooth a 366-element array with a centred moving mean wrapping around.
    arr: (366, 60, 60) or (366,) array
    day d averages days d-15 ... d+15, counted modulo 366.
    """
    half = window // 2  # 15
    n = 366
    
    if arr.ndim == 1:
        # For 1D array
        result = np.zeros(n)
        for d in range(n):
            indices = [(d - half + k) % n for k in range(window)]
            result[d] = np.mean(arr[indices])
        return result
    elif arr.ndim == 3:
        # For (366, 60, 60) array
        result = np.zeros_like(arr)
        for d in range(n):
            indices = [(d - half + k) % n for k in range(window)]
            result[d] = np.mean(arr[indices], axis=0)
        return result
    else:
        raise ValueError(f"Unsupported array dimension: {arr.ndim}")

# Smooth
print("Smoothing thresholds...")
smooth_thresholds = smooth_wrap(thresholds)
print("Smoothing climatology...")
smooth_climatology = smooth_wrap(climatology)

# Check
print(f"Threshold at doy 1, cell (0,0): {smooth_thresholds[0, 0, 0]}")
print(f"Threshold at doy 153, cell (0,0): {smooth_thresholds[152, 0, 0]}")
print(f"Climatology at doy 153, cell (0,0): {smooth_climatology[152, 0, 0]}")

# Check that smoothing wraps around (day 1 and day 366 use values from days near year boundary)
print(f"Threshold at doy 1: {smooth_thresholds[0, 0, 0]}")
print(f"Threshold at doy 366: {smooth_thresholds[365, 0, 0]}")
print(f"Threshold at doy 2: {smooth_thresholds[1, 0, 0]}")
print(f"Threshold at doy 365: {smooth_thresholds[364, 0, 0]}")

np.save('/work/smooth_thresholds.npy', smooth_thresholds)
np.save('/work/smooth_climatology.npy', smooth_climatology)
print("Saved smoothed data.")
