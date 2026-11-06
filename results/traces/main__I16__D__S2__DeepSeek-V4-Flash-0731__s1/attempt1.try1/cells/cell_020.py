
import numpy as np

# Load saved raw values
threshold = np.load('/work/threshold_raw.npy')
climatology = np.load('/work/climatology_raw.npy')

print("Shape:", threshold.shape)

# Smooth with 31-day centred moving average wrapping around (mod 366)
def smooth_31(arr):
    """arr: (366, lat, lon), smooth along axis 0 with 31-day centred moving avg wrapping."""
    # Pad by 15 at each end (wrapping)
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)  # (396, lat, lon)
    # Moving average with window 31
    kernel = np.ones(31) / 31.0
    # Use convolution along axis 0
    result = np.zeros_like(arr)
    # Vectorized: use sliding_window_view or manual approach
    from numpy.lib.stride_tricks import sliding_window_view
    windows = sliding_window_view(padded, 31, axis=0)  # (366, 31, lat, lon)
    result = np.mean(windows, axis=1)  # (366, lat, lon)
    return result

threshold_smooth = smooth_31(threshold)
climatology_smooth = smooth_31(climatology)

print("After smoothing:")
print("NaNs in threshold_smooth:", np.sum(np.isnan(threshold_smooth)))
print("NaNs in climatology_smooth:", np.sum(np.isnan(climatology_smooth)))
print("Sample threshold_smooth[0,:3,0]:", threshold_smooth[0,:3,0])
print("Sample climatology_smooth[0,:3,0]:", climatology_smooth[0,:3,0])

np.save('/work/threshold_smooth.npy', threshold_smooth)
np.save('/work/climatology_smooth.npy', climatology_smooth)
