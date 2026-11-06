
import numpy as np

# Test smooth_wrap on a simple case
arr = np.zeros(366)
arr[:] = np.arange(1, 367)  # arr[i] = i+1 for doy i+1

def smooth_wrap(arr):
    result = np.full_like(arr, np.nan)
    for d in range(366):
        vals = []
        for offset in range(-15, 16):
            idx = (d + offset) % 366
            if not np.isnan(arr[idx]):
                vals.append(arr[idx])
        if len(vals) > 0:
            result[d] = np.mean(vals)
    return result

result = smooth_wrap(arr.astype(float))
# For doy 1 (index 0), the average of indices 0-15 and 351-365
# That's days 1-16 and 352-366
# But wait, with modulo 366, for index 0, offsets -15 to 15 give:
# indices 351, 352, ..., 365, 0, 1, ..., 15
# So days 352-366 and 1-16
expected = np.mean(list(range(352, 367)) + list(range(1, 17)))
print(f"Expected for doy 1: {expected}")
print(f"Got: {result[0]}")

# For doy 100 (index 99), offsets -15 to 15 give indices 84-114 (days 85-115)
expected = np.mean(range(85, 116))
print(f"Expected for doy 100: {expected}")
print(f"Got: {result[99]}")

# For doy 366 (index 365), offsets -15 to 15 give indices 350-365 and 0-14
# Days 351-366 and 1-15
expected = np.mean(list(range(351, 367)) + list(range(1, 16)))
print(f"Expected for doy 366: {expected}")
print(f"Got: {result[365]}")
