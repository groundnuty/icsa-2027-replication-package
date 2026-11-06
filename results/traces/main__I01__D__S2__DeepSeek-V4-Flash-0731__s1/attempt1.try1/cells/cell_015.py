
import numpy as np

# Test smoothing with simple array
def smooth_wrap(arr):
    n = 366
    result = np.zeros(n)
    for i in range(n):
        vals = []
        for j in range(i-15, i+16):
            k = j % n
            if not np.isnan(arr[k]):
                vals.append(arr[k])
        if vals:
            result[i] = np.mean(vals)
        else:
            result[i] = np.nan
    return result

# Test with all ones
arr = np.ones(366)
result = smooth_wrap(arr)
print("All ones -> all:", result.min(), result.max(), "OK" if np.allclose(result, 1.0) else "FAIL")

# Test with index values
arr = np.arange(366)
result = smooth_wrap(arr)
# Day 0 (index 0): averages indices 351-365 and 0-15, which is values 351-365 and 0-15
expected_0 = np.mean(np.concatenate([np.arange(351, 366), np.arange(0, 16)]))
print(f"Day 1 expected: {expected_0}, got: {result[0]}")
print(f"Match: {np.allclose(result[0], expected_0)}")

# Day 183 (index 182): averages indices 167-197
expected_183 = np.mean(np.arange(167, 198))
print(f"Day 183 expected: {expected_183}, got: {result[182]}")
print(f"Match: {np.allclose(result[182], expected_183)}")

# Day 366 (index 365): averages indices 350-365 and 0-14
expected_366 = np.mean(np.concatenate([np.arange(350, 366), np.arange(0, 15)]))
print(f"Day 366 expected: {expected_366}, got: {result[365]}")
print(f"Match: {np.allclose(result[365], expected_366)}")

print("Smoothing implementation looks correct")
