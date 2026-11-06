
import numpy as np

# Test numpy quantile with hazen method
arr = np.array([1.0, 2.0, 3.0, 4.0])
try:
    result = np.quantile(arr, 0.9, method='hazen')
    print(f"quantile with hazen: {result}")
except Exception as e:
    print(f"Error: {e}")

# Also test with NaN
arr_nan = np.array([1.0, np.nan, 3.0, 4.0])
try:
    result = np.quantile(arr_nan, 0.9, method='hazen')
    print(f"quantile with hazen and NaN: {result}")
except Exception as e:
    print(f"Error with NaN: {e}")

# Manual computation of Hyndman-Fan type 5
# Type 5: h = (N-1)p + 1, Q(p) = x_floor(h) + (h - floor(h))(x_ceil(h) - x_floor(h))
# where x is sorted data
def hazen_quantile(data, p):
    data = np.sort(data)
    n = len(data)
    h = (n - 1) * p + 1  # 1-indexed position
    if h < 1:
        return data[0]
    if h > n:
        return data[-1]
    h_floor = int(np.floor(h))
    h_ceil = int(np.ceil(h))
    if h_floor == h_ceil:
        return data[h_floor - 1]
    frac = h - h_floor
    return data[h_floor - 1] + frac * (data[h_ceil - 1] - data[h_floor - 1])

manual = hazen_quantile(np.array([1.0, 2.0, 3.0, 4.0]), 0.9)
print(f"Manual hazen: {manual}")
