import numpy as np

threshold = np.load('/tmp/work/threshold_raw.npy')
climatology = np.load('/tmp/work/climatology_raw.npy')

print(f"threshold shape: {threshold.shape}")
print(f"climatology shape: {climatology.shape}")

# Apply 31-day centered moving mean with wrap-around
def smooth_366(arr):
    """Smooth a 366-element array with a 31-day centered moving mean that wraps."""
    # arr has shape (366, ...) - smooth along axis 0
    n = arr.shape[0]  # should be 366
    
    # Pad the array by 15 on both ends (wrap-around)
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    
    # Compute cumulative sum along axis 0
    # Use np.convolve or a manual approach
    result = np.zeros_like(arr)
    
    for i in range(n):
        # Window: days i-15 to i+15 (modulo 366)
        start = i  # in padded coordinates, day i in original is at position 15+i
        # Days d-15 .. d+15 in padded coords: (15+i-15) to (15+i+15)
        window = padded[15+i-15:15+i+16]
        result[i] = np.mean(window, axis=0)
    
    return result

# Actually, this is simpler with np.convolve or rolling mean
def smooth_366_fast(arr):
    """Efficiently smooth a (366, ...) array along axis 0 with 31-day centered moving mean."""
    n = arr.shape[0]
    # Pad with wrap-around
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    
    # Use cumulative sum for efficiency
    # cumsum of padded along axis 0
    cumsum = np.cumsum(padded, axis=0)
    
    result = np.zeros_like(arr)
    for i in range(n):
        start = i  # padded index for original day i is at position 15 + i
        # Window: original days (i-15) to (i+15), padded indices (15+i-15) to (15+i+15)
        s = 15 + i - 15  # = i
        e = 15 + i + 16  # = i + 31
        if s == 0:
            result[i] = cumsum[e-1] / 31.0
        else:
            result[i] = (cumsum[e-1] - cumsum[s-1]) / 31.0
    
    return result

# Test on a small array first
test = np.arange(366, dtype=np.float64)
smoothed_test = smooth_366_fast(test)
# Verify: day 0 averages days 351..365 and 0..15 (i.e., 366-15=351 through 15)
expected = np.mean(np.arange(351, 366) + np.arange(0, 16)) / 1.0  # This is wrong
# Actually, let me just verify manually
# Day 0 (index 0) averages days 366-15=351 through 15 (indices 351..365, 0..15)
vals = np.concatenate([np.arange(351, 366), np.arange(0, 16)])
expected_0 = np.mean(vals)
print(f"Test day 0: {smoothed_test[0]}, expected: {expected_0}")
assert np.isclose(smoothed_test[0], expected_0), "Smoothing test failed!"

# Day 100 averages days 85-115
expected_100 = np.mean(np.arange(85, 116))
print(f"Test day 100: {smoothed_test[100]}, expected: {expected_100}")
assert np.isclose(smoothed_test[100], expected_100), "Smoothing test failed!"

print("Smoothing test passed!")

# Apply smoothing to threshold and climatology
threshold_smooth = smooth_366_fast(threshold)
climatology_smooth = smooth_366_fast(climatology)

print(f"threshold_smooth shape: {threshold_smooth.shape}")
print(f"climatology_smooth shape: {climatology_smooth.shape}")

# Save smoothed results
np.save('/tmp/work/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/work/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed threshold and climatology.")

# Check some sea cell values
# Find a sea cell (finite on day 1)
sea_cells = np.isfinite(threshold_smooth[0])
print(f"Sea cells on day 1: {sea_cells.sum()}")
if sea_cells.sum() > 0:
    idx = np.argwhere(sea_cells)[0]
    print(f"First sea cell: {idx}")
    print(f"  Threshold day 153: {threshold_smooth[152, idx[0], idx[1]]}")
    print(f"  Climatology day 153: {climatology_smooth[152, idx[0], idx[1]]}")
