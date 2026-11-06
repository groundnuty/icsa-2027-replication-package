
import numpy as np

thresholds = np.load('/work/thresholds_raw.npy')  # (366, 60, 60)
climatologies = np.load('/work/climatologies_raw.npy')

# Check NaN pattern
nan_mask = np.isnan(thresholds[0, :, :])
print(f"NaN cells at day 1: {nan_mask.sum()}")
print(f"Total cells: {nan_mask.size}")

# Smooth with 31-day moving average wrapping around the year
def smooth_wrap(arr):
    """Smooth a 366-element array with a centred 31-day moving mean, wrapping around."""
    # arr has shape (366, n_lat, n_lon)
    # For each day d, average days d-15 to d+15 (mod 366)
    n = arr.shape[0]  # 366
    result = np.zeros_like(arr)
    
    # Use rolling with padding
    # Create padded version
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)  # (366+30, ...)
    
    for d in range(n):
        # Days d-15 to d+15 in padded coordinates
        # Padded index for day d is d+15
        start = d  # padded index for d-15 (since original index d-15 -> padded index d-15+15 = d)
        end = d + 31  # padded index for d+15 (since original index d+15 -> padded index d+15+15 = d+30, exclusive so end=d+31)
        result[d] = np.mean(padded[start:end], axis=0)
    
    return result

# Apply smoothing
thresholds_smooth = smooth_wrap(thresholds)
climatologies_smooth = smooth_wrap(climatologies)

# Check
print(f"\nThreshold smoothed sample (day 1): {thresholds_smooth[0, 0, 0]:.4f}")
print(f"Climatology smoothed sample (day 1): {climatologies_smooth[0, 0, 0]:.4f}")

# Check that smoothing fills in NaN values in sea cells
nan_before = np.isnan(thresholds).sum(axis=0)
nan_after = np.isnan(thresholds_smooth).sum(axis=0)
print(f"\nNaN cells per cell (before): min={nan_before.min()}, max={nan_before.max()}")
print(f"NaN cells per cell (after): min={nan_after.min()}, max={nan_after.max()}")

# The smoothing should average over all days. If a cell is land (all NaN), it stays NaN.
# If a cell has some valid days, the moving average will have values on those days.

# Save
np.save('/work/thresholds_smooth.npy', thresholds_smooth)
np.save('/work/climatologies_smooth.npy', climatologies_smooth)
print("\nSaved smoothed thresholds and climatologies.")
