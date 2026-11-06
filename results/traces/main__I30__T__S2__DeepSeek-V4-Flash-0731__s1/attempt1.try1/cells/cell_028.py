
import numpy as np

# Test Hazen percentile with different data
# For [1,2,3,4,5], 90th percentile
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

# Check numpy method
p = np.percentile(x, 90, method='hazen')
print(f"Hazen 90th percentile of [1,2,3,4,5]: {p}")

# Manual calculation
# Hazen method (type 5): 
# h = (n-1) * p + 1 where p is the fraction (0.9)
# For n=5, p=0.9: h = 4 * 0.9 + 1 = 4.6
# The h-th quantile: x[floor(h)-1] + (h - floor(h)) * (x[ceil(h)-1] - x[floor(h)-1])
# floor(4.6) = 4, ceil(4.6) = 5
# x[3] + 0.6 * (x[4] - x[3]) = 4 + 0.6 = 4.6

# Let me check what numpy's hazen method actually computes
# From numpy docs: "hazen: h = (n-1)*p + 1/2" ??? No wait...
# Actually let me check numpy source

# Numpy method descriptions:
# hazen: h = (n - 1) * p + 1/2 ... no wait, that doesn't sound right
# Let me look at the actual implementation

# From numpy docs for percentile methods:
# type 5 (Hazen): h = (n-1)*p + 1, piecewise linear interpolation
#   where h is in [1, n], x = x[h] if integer, else interpolate between x[floor(h)] and x[ceil(h)]
#   using 0-indexed: x[h-1] if integer, else x[floor(h)-1] + (h - floor(h)) * (x[ceil(h)-1] - x[floor(h)-1])

# Wait, but there's a subtlety. Let me check:
# In numpy, method="hazen" uses "piecewise-linear interpolation" with h = (n-1)*p + 1
# h is then used to find the quantile.

# For n=5, p=0.9: h = 4*0.9 + 1 = 4.6
# floor(h) = 4, so we interpolate between x[3] and x[4] (0-indexed)
# x[3] + 0.6 * (x[4] - x[3]) = 4 + 0.6 = 4.6

# But numpy returned 5.0. Let me check if maybe numpy has a different convention.

# Let me try with more data
x2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
p2 = np.percentile(x2, 90, method='hazen')
print(f"Hazen 90th percentile of [1..10]: {p2}")
# h = 9*0.9 + 1 = 9.1
# x[8] + 0.1*(x[9]-x[8]) = 9 + 0.1 = 9.1
print(f"Expected: 9.1")

# Let me try another
x3 = np.array([2.0, 4.0, 6.0, 8.0])
p3 = np.percentile(x3, 25, method='hazen')
print(f"Hazen 25th percentile of [2,4,6,8]: {p3}")
# h = 3*0.25 + 1 = 1.75
# x[0] + 0.75*(x[1]-x[0]) = 2 + 0.75*2 = 3.5
