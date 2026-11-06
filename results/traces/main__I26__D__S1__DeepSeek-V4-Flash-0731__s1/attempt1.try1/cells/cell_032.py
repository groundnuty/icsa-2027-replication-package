import numpy as np

# Load intermediate results
threshold = np.load('/work/threshold_raw.npy')
climatology = np.load('/work/climatology_raw.npy')

print("Threshold shape:", threshold.shape)
print("Climatology shape:", climatology.shape)

# Apply 31-day centered moving mean with wrap-around (mod 366)
# For each cell and day d (0-indexed 0-365), average days (d-15) to (d+15) mod 366
def smooth_366(arr):
    """Apply 31-day centered moving mean with wrap-around to 366-element array."""
    n = 366
    window = 31
    half = 15
    result = np.zeros_like(arr)
    for d in range(n):
        indices = [(d - half + k) % n for k in range(window)]
        result[d] = np.mean(arr[indices])
    return result

# Apply to each cell
# Vectorized: for each cell, smooth the 366-element array
# We can do this with np.convolve after creating a wrapped version
def smooth_366_vectorized(arr_2d):
    """arr_2d: (60, 60, 366), smooth along last axis with wrap-around."""
    n = 366
    half = 15
    # Create padded version: repeat first 15 and last 15
    padded = np.concatenate([arr_2d[:, :, -half:], arr_2d, arr_2d[:, :, :half]], axis=2)
    # Apply moving average with kernel
    kernel = np.ones(31) / 31.0
    # Use convolution
    result = np.zeros_like(arr_2d)
    for i in range(60):
        for j in range(60):
            result[i, j, :] = np.convolve(padded[i, j], kernel, mode='valid')
    return result

# Let me try a faster approach using stride tricks or just direct computation
# Actually, let me just do it with numpy efficiently

def smooth_366_fast(arr):
    """arr: (..., 366), smooth along last axis with 31-day wrap-around window."""
    shape = arr.shape
    n = shape[-1]
    half = 15
    
    # Pad the last axis: prepend last 15, append first 15
    pad = np.concatenate([arr[..., -half:], arr, arr[..., :half]], axis=-1)
    
    # Compute cumulative sum along last axis
    csum = np.cumsum(pad, axis=-1)
    
    # For window positions d in 0..365, the window is pad[d:d+31]
    # The sum is csum[d+31] - csum[d] for d=0..365
    window_sum = csum[..., 31:] - csum[..., :-31]
    
    # window_sum shape is (..., 366)
    result = window_sum / 31.0
    return result

# Verify shapes
print("Verifying smoothing function...")
test = np.random.randn(60, 60, 366)
result = smooth_366_fast(test)
print("Result shape:", result.shape)

# Test with known pattern
test2 = np.zeros((1, 1, 366))
test2[0, 0, 0] = 1.0
result2 = smooth_366_fast(test2)
print(f"Test: position 0, window 31 (indices 351-365, 0-15), sum={result2[0,0,0]:.4f}")
# The window for day 0 (index 0) should be days 351-365 and 0-15 = 31 days
# But day 0 has value 1, all others 0, so mean = 1/31
print(f"Expected: 1/31 = {1/31:.4f}")
# Check day 15 (should include index 0 in its window)
# Day 15's window: indices 0-30 (in padded: positions 15+15=30 in original to...)
# Actually, let me check day 15: window is days 0-30, so includes day 0
# mean = 1/31
print(f"Day 15 value: {result2[0,0,15]:.4f}")

# Check day 16: window is days 1-31, doesn't include day 0
print(f"Day 16 value: {result2[0,0,16]:.4f}")
