
import numpy as np

# Test smoothing manually
arr = np.arange(366, dtype=np.float64)

# Manual smoothing for index 0: mean of arr[351:366] and arr[0:16]
expected_0 = np.mean(np.concatenate([arr[-15:], arr[:16]]))
print(f"Manual smoothing at index 0: {expected_0}")

# My function
def smooth_31(arr):
    n = 366
    window = 31
    half = 15
    padded = np.concatenate([arr[-half:], arr, arr[:half]])
    result = np.zeros_like(arr)
    for i in range(n):
        result[i] = np.mean(padded[i:i+window])
    return result

result = smooth_31(arr)
print(f"My function at index 0: {result[0]}")
print(f"Match: {np.isclose(result[0], expected_0)}")

# Check index 15 (should include days 0-30)
expected_15 = np.mean(arr[0:31])
print(f"Manual at index 15: {expected_15}, mine: {result[15]}, match: {np.isclose(result[15], expected_15)}")

# Check index 350 (should include days 335-365 and wrap to 0-5... wait)
# For index 350: days (350-15)=335 to (350+15)=365 mod 366 = 335-365
expected_350 = np.mean(arr[335:366])
print(f"Manual at index 350: {expected_350}, mine: {result[350]}, match: {np.isclose(result[350], expected_350)}")

# Check index 360: days 345-366(0) and 0-9... wait
# days (360-15)=345 to (360+15)=375 mod 366 = 345-365, 0-9
expected_360 = np.mean(np.concatenate([arr[345:366], arr[0:10]]))
print(f"Manual at index 360: {expected_360}, mine: {result[360]}, match: {np.isclose(result[360], expected_360)}")
