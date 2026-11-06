
import numpy as np

# Test Hazen percentile
# MATLAB's quantile(x, 0.9) uses Hyndman-Fan type 5: h = N*p + 0.5
# For N=10, p=0.9: h = 10*0.9 + 0.5 = 9.5
# Sorted data, index = floor(9.5)-1 = 8 (0-based), frac = 0.5
# Result = x[8] + 0.5*(x[9]-x[8])

x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
print(f"np.percentile(x, 90, method='hazen') = {np.percentile(x, 90, method='hazen')}")
print(f"Expected: 9.5")

# Test with a different array
x2 = np.array([5, 1, 3, 2, 4])
print(f"np.percentile(x2, 90, method='hazen') = {np.percentile(x2, 90, method='hazen')}")
# N=5, h = 5*0.9 + 0.5 = 5.0
# index = 4 (0-based), frac = 0
# Sorted: [1,2,3,4,5], x[4] = 5
print(f"Expected: 5")
