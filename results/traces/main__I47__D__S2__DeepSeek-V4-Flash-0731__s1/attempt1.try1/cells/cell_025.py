
import numpy as np

# Test smooth_wrap on a simple array
def smooth_wrap(arr):
    n = arr.shape[0]
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    result = np.zeros_like(arr)
    for i in range(n):
        result[i] = np.nanmean(padded[i:i+31], axis=0)
    return result

# Test with 1D array of length 366
arr = np.arange(1, 367, dtype=np.float64)

# For day 1 (index 0), the mean should be over days 352-366 and 1-16
expected_day1 = np.mean(np.concatenate([arr[351:366], arr[0:16]]))
# Wait, let me recalculate. arr[351] = 352 (1-indexed day 352), arr[365] = 366
# So arr[351:366] = days 352-366, arr[0:16] = days 1-16
# But the spec says day d averages days d-15 to d+15. For day 1: days -14 to 16.
# Modulo 366: days 352 to 366 and 1 to 16.
# arr[351:366] covers days 352-366 (15 days), arr[0:16] covers days 1-16 (16 days)
# Total: 15+16 = 31 days. ✓

result = smooth_wrap(arr)
print("Day 1 (index 0) smoothed:", result[0])
print("Expected:", expected_day1)

# For day 183 (index 182), window is days 168-198
expected_day183 = np.mean(arr[167:198])  # days 168-198 (1-indexed), indices 167-197 (0-indexed)
print("Day 183 smoothed:", result[182])
print("Expected:", expected_day183)

# For day 366 (index 365), window is days 351-366 and 1-15
expected_day366 = np.mean(np.concatenate([arr[350:366], arr[0:15]]))
print("Day 366 smoothed:", result[365])
print("Expected:", expected_day366)

# Verify
print("\nAll checks:", np.isclose(result[0], expected_day1) and np.isclose(result[182], expected_day183) and np.isclose(result[365], expected_day366))
