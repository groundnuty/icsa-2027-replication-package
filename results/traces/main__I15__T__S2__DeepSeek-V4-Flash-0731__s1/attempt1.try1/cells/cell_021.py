
import numpy as np

threshold = np.load('threshold_raw.npy')
climatology = np.load('climatology_raw.npy')

def smooth_wrap(arr, window=31, doy_len=366):
    """Smooth 366-element arrays (indices 1..366 in arr) with centred moving average wrapping around.
    arr has shape (367, n_lat, n_lon). Returns smoothed array of shape (367, n_lat, n_lon).
    """
    half = window // 2
    data = arr[1:367].copy()  # shape (366, n_lat, n_lon)
    n_lat, n_lon = data.shape[1], data.shape[2]
    
    accum = np.zeros_like(data, dtype=np.float64)
    count = np.zeros_like(data, dtype=np.float64)
    
    for offset in range(-half, half + 1):
        rolled = np.roll(data, -offset, axis=0)
        valid = ~np.isnan(rolled)
        accum[valid] += rolled[valid]
        count[valid] += 1
    
    smoothed = np.where(count > 0, accum / np.where(count > 0, count, 1), np.nan)
    
    result = np.full_like(arr, np.nan)
    result[1:367] = smoothed
    return result

threshold_smooth = smooth_wrap(threshold)
climatology_smooth = smooth_wrap(climatology)

print('Threshold smoothed shape:', threshold_smooth.shape)
# Check sample
print('Sample threshold before/after smoothing:')
print('  Before:', threshold[150, 30, 30], threshold[100, 30, 30], threshold[200, 30, 30])
print('  After:', threshold_smooth[150, 30, 30], threshold_smooth[100, 30, 30], threshold_smooth[200, 30, 30])

# Check NaN preservation
print('NaN in smoothed threshold:', np.isnan(threshold_smooth[1:367]).sum())
print('NaN in original threshold:', np.isnan(threshold[1:367]).sum())

np.save('threshold_smooth.npy', threshold_smooth)
np.save('climatology_smooth.npy', climatology_smooth)
