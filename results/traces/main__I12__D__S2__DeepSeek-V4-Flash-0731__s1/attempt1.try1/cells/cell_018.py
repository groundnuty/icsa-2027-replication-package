
import numpy as np

# Verify numpy method='hazen' is the same as MATLAB's default quantile (type 5, Hyndman-Fan)
# MATLAB default uses 'method 5' in the Hyndman-Fan classification
# numpy method='hazen' corresponds to Hyndman-Fan type 5

# Test with a simple array
x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
q = np.quantile(x, 0.9, method='hazen')
print(f"quantile with hazen: {q}")

# MATLAB's quantile with default method: interpolation based on
# position = (n-1)*p + 1 for the default, or... 
# Actually, MATLAB's default quantile uses linear interpolation with index (n-1)*p + 1
# numpy's hazen method uses position (n + 1/3) * p + 1/3, which is Hyndman-Fan type 5

# Let me check what numpy does with hazen
print("Hazen method formula: (n + 1/3)*p + 1/3")
n = len(x)
p = 0.9
h = (n + 1/3) * p + 1/3
print(f"h = {h}")
# Linear interpolation
idx_floor = int(np.floor(h))
idx_ceil = int(np.ceil(h))
frac = h - idx_floor
if idx_ceil < len(x):
    val = x[idx_floor - 1] + frac * (x[idx_ceil - 1] - x[idx_floor - 1])
else:
    val = x[idx_floor - 1]
print(f"Manual calculation: {val}")

# Let me verify with numpy directly
print(f"numpy hazen: {np.quantile(x, 0.9, method='hazen')}")
