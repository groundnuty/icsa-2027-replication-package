
import numpy as np

# Verify np.nanquantile with method='hazen' vs MATLAB quantile type 5
# Simple example
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
result = np.quantile(data, 0.9, method='hazen')
print(f"np.quantile hazen 90th: {result}")

# MATLAB quantile default (type 5):
# For a vector x of length n, q = quantile(x, p):
# h = (n-1)*p + 1
# q = x[floor(h)] + (h - floor(h)) * (x[floor(h)+1] - x[floor(h)])
n = len(data)
p = 0.9
h = (n - 1) * p + 1
print(f"h = {h}")
x_sorted = np.sort(data)
idx = int(np.floor(h)) - 1  # 0-indexed
frac = h - np.floor(h)
q = x_sorted[idx] + frac * (x_sorted[idx + 1] - x_sorted[idx])
print(f"MATLAB quantile: {q}")

# Test with NaN
data_nan = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
result_nan = np.nanquantile(data_nan, 0.9, method='hazen')
print(f"np.nanquantile hazen 90th (with NaN): {result_nan}")

# MATLAB equivalent ignoring NaN:
data_valid = data_nan[~np.isnan(data_nan)]
n = len(data_valid)
h = (n - 1) * p + 1
x_sorted = np.sort(data_valid)
idx = int(np.floor(h)) - 1
frac = h - np.floor(h)
q = x_sorted[idx] + frac * (x_sorted[idx + 1] - x_sorted[idx])
print(f"MATLAB quantile (ignoring NaN): {q}")

# Verify they match
print(f"Match: {result_nan == q}")
