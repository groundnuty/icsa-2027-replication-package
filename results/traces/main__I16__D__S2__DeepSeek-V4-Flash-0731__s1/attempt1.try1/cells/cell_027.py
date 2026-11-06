
import numpy as np

threshold = np.load('/work/threshold_raw.npy')
climatology = np.load('/work/climatology_raw.npy')

def smooth_31(arr):
    """Smooth along axis 0 with 31-day centred moving average wrapping around."""
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    from numpy.lib.stride_tricks import sliding_window_view
    windows = sliding_window_view(padded, 31, axis=0)
    # windows shape: (366, 60, 60, 31)
    result = np.mean(windows, axis=-1)
    return result

threshold_smooth = smooth_31(threshold)
climatology_smooth = smooth_31(climatology)

print("threshold_smooth shape:", threshold_smooth.shape)
print("climatology_smooth shape:", climatology_smooth.shape)

# Verify the first element is the mean of doys 366-15..366, 1..16 (i.e., doys 352-366, 1-16) in the raw array
# Day 1 (index 0) averages doys 352-366, 1-16 (31 days total, wrapping)
# In the padded array, arr[0] corresponds to padded index 15
# padded[0:31] = arr[-15:366] + arr[0:16] = arr[351:366] + arr[0:16]
expected = np.nanmean(threshold[np.concatenate([np.arange(351, 366), np.arange(0, 16)])], axis=0)
actual = threshold_smooth[0]
print("Max diff for day 1:", np.nanmax(np.abs(expected - actual)))

# Check all values finite for sea cells
print("NaNs in threshold_smooth:", np.sum(np.isnan(threshold_smooth)))
print("NaNs in climatology_smooth:", np.sum(np.isnan(climatology_smooth)))

np.save('/work/threshold_smooth.npy', threshold_smooth)
np.save('/work/climatology_smooth.npy', climatology_smooth)
