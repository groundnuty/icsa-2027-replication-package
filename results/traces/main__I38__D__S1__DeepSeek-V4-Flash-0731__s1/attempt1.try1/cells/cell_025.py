
import numpy as np

# Test smooth_wrap on a simple case
def smooth_wrap(arr):
    """Smooth a 366-element array with 31-day moving avg wrapping around."""
    result = np.zeros_like(arr)
    for d in range(366):
        total = 0.0
        count = 0
        for offset in range(-15, 16):
            idx = (d + offset) % 366
            if np.isfinite(arr[idx]):
                total += arr[idx]
                count += 1
        if count > 0:
            result[d] = total / count
        else:
            result[d] = np.nan
    return result

# Test with constant array
arr = np.ones(366)
result = smooth_wrap(arr)
print("Constant array test - all values:", np.all(result == 1.0))

# Test with known pattern
arr = np.zeros(366)
arr[:31] = 1.0  # first 31 days are 1
result = smooth_wrap(arr)
# Day 15 should average days 0-30 (indices 0-30), all 1s
print(f"Day 15 (index 15) result: {result[15]}")
# Day 0 should average indices 351-365 (wrapped) and 0-15
# Indices 351-365 are 0 (since arr[:31] covers indices 0-30)
# Indices 0-15 are 1
# So average = 16/31
expected = 16.0 / 31.0
print(f"Day 0 (index 0) result: {result[0]}, expected: {expected}")

# Verify array length
print(f"Input length: {len(arr)}, Output length: {len(result)}")

# Verify that smoothing preserves length and wraps correctly
# Day 365 should average indices 350-365 (0s) and 0-14 (1s)
# So average = 15/31
expected_365 = 15.0 / 31.0
print(f"Day 365 (index 365) result: {result[365]}, expected: {expected_365}")
