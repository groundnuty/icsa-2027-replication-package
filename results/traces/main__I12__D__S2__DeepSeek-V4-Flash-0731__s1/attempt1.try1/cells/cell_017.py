
import numpy as np

# Test smooth_31day on a simple array
def smooth_31day(arr):
    """Smooth a 366-element array with unweighted centred 31-day moving mean that wraps around."""
    result = np.zeros_like(arr)
    for d in range(366):
        result[d] = np.mean(arr[(np.arange(d-15, d+16) % 366)])
    return result

# Test with identity array
test = np.arange(366, dtype=float)
result = smooth_31day(test)
# Check day 0 (index 0): average of indices 351..365, 0..15 (wrapping)
expected_0 = np.mean(np.concatenate([np.arange(351, 366), np.arange(0, 16)]))
print(f"Day 0 (doy 1): {result[0]}, expected {expected_0}")

# Check day 30 (index 30): average of indices 15..45
expected_30 = np.mean(np.arange(15, 46))
print(f"Day 30: {result[30]}, expected {expected_30}")

# Check day 365 (index 365): average of indices 350..365, 0..14
expected_365 = np.mean(np.concatenate([np.arange(350, 366), np.arange(0, 15)]))
print(f"Day 365: {result[365]}, expected {expected_365}")
