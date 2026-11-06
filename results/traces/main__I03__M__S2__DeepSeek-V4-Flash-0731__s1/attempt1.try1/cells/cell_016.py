
import numpy as np

# threshold and climatology shape: (366, 60, 60)
# Apply 31-day centred moving average wrapping around
def smooth_wrap(arr):
    """Apply unweighted centred 31-day moving mean wrapping around year.
    arr shape: (366, ...)"""
    # Pad with 15 days on each side (wrapping)
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    # shape: (396, ...)
    
    # Compute moving mean with window 31
    n = padded.shape[0]
    result = np.zeros_like(arr)
    for i in range(366):
        result[i] = np.mean(padded[i:i+31], axis=0)
    return result

threshold_smooth = smooth_wrap(threshold)
climatology_smooth = smooth_wrap(climatology)

print("Smoothed threshold shape:", threshold_smooth.shape)
print("Smoothed climatology shape:", climatology_smooth.shape)
print("Sample threshold values (doy 152, lat 20, lon 20):", threshold_smooth[151, 20, 20])
print("Sample climatology values (doy 152, lat 20, lon 20):", climatology_smooth[151, 20, 20])
