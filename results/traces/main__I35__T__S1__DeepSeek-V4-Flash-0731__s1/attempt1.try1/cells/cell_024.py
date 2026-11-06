
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')  # (366, 60, 60)
climatology_raw = np.load('/tmp/climatology_raw.npy')

# Apply 31-day centered moving mean with wrap-around
# day d averages days d-15 to d+15, counted modulo 366
n_doy = 366
window = 31
half = 15

def smooth_wrap(arr):
    """Smooth a (366, ...) array with 31-day centered moving mean that wraps around."""
    # arr has shape (366, ...) 
    result = np.zeros_like(arr)
    n = arr.shape[0]
    for d in range(n):
        # Collect indices d-15 to d+15 modulo 366
        indices = [(d + offset) % n for offset in range(-half, half+1)]
        result[d] = np.mean(arr[indices], axis=0)
    return result

threshold_smooth = smooth_wrap(threshold_raw)
climatology_smooth = smooth_wrap(climatology_raw)

print("Smoothed")
# Verify for a sea cell
sea_indices = np.argwhere(np.any(np.isfinite(threshold_raw), axis=0))
print(f"Sea cells in threshold: {len(sea_indices)}")

# Check a sample
si, sj = sea_indices[0]
print(f"Cell ({si},{sj}):")
print(f"  Raw threshold doy 153: {threshold_raw[152, si, sj]}")
print(f"  Smooth threshold doy 153: {threshold_smooth[152, si, sj]}")
print(f"  Raw clim doy 153: {climatology_raw[152, si, sj]}")
print(f"  Smooth clim doy 153: {climatology_smooth[152, si, sj]}")

# Check smoothing at day 1 (wrap-around)
print(f"  Raw threshold doy 1: {threshold_raw[0, si, sj]}")
print(f"  Smooth threshold doy 1: {threshold_smooth[0, si, sj]}")

np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed")
