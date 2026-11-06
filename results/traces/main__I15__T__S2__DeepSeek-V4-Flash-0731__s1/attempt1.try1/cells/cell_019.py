
import numpy as np

threshold = np.load('threshold_raw.npy')
climatology = np.load('climatology_raw.npy')
print('Shapes:', threshold.shape, climatology.shape)

def smooth_wrap_vectorized(arr, window=31, doy_len=366):
    """Smooth 366-element arrays (indices 1..366 in arr) with a centred moving average that wraps.
    arr has shape (367, n_lat, n_lon).
    """
    n_lat, n_lon = arr.shape[1], arr.shape[2]
    half = window // 2
    
    # Extract the DOY 1-366 data: shape (366, n_lat, n_lon)
    data = arr[1:367].copy()  # shape (366, n_lat, n_lon)
    
    # Create smoothed output: shape (366, n_lat, n_lon)
    smoothed = np.full_like(data, np.nan)
    
    # For each day d (0-indexed in data, representing DOY d+1):
    # average data[(d-15) % 366 : (d+16) % 366], wrapping around
    # We can use np.roll to handle wrapping
    # Build the result by accumulating
    accum = np.zeros_like(data)
    count = np.zeros_like(data, dtype=np.float64)
    
    for offset in range(-half, half + 1):
        rolled = np.roll(data, -offset, axis=0)
        valid = ~np.isnan(rolled)
        accum[valid] += rolled[valid]
        count[valid] += 1
    
    smoothed = np.where(count > 0, accum / np.where(count > 0, count, 1), np.nan)
    return smoothed

# Test on small example
test = np.full((367, 2, 2), 1.0)
test[1:367] = np.arange(366)[:, None, None] + 0.0
result = smooth_wrap_vectorized(test)
print('Test result shape:', result.shape)
print('Test first few:', result[0, 0, 0], result[1, 0, 0], result[100, 0, 0])
# For a constant array, smoothed should be the same as input
# For linear array with mean window, it should be approximately the middle value
