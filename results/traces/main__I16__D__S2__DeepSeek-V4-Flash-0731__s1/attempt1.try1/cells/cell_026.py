
import numpy as np

# Reload raw
threshold = np.load('/work/threshold_raw.npy')
print("Raw threshold shape:", threshold.shape)

# Re-do smoothing
def smooth_31(arr):
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    print("Padded shape:", padded.shape)
    from numpy.lib.stride_tricks import sliding_window_view
    windows = sliding_window_view(padded, 31, axis=0)
    print("Windows shape:", windows.shape)
    result = np.mean(windows, axis=1)
    print("Result shape:", result.shape)
    return result

threshold_smooth = smooth_31(threshold)
print("Final threshold_smooth shape:", threshold_smooth.shape)
