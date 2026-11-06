
import numpy as np

# Verify numpy's percentile with method='hazen' matches MATLAB's quantile default
# MATLAB's quantile(x, 0.9) uses linear interpolation (Hyndman-Fan type 5)
# numpy's percentile with method='hazen' should give the same result

# Test with a simple array
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("numpy hazen 90th percentile:", np.percentile(x, 90, method='hazen'))
# MATLAB would compute: q = 0.9*(n-1)+1 = 0.9*4+1 = 4.6, so value = x[4] + 0.6*(x[5]-x[4])
# But there are only 5 elements (indices 0-4). Let me check.
# Actually, MATLAB's quantile uses 0-based indexing for the position.
# Position = 0.9*(5-1) + 1 = 4.6. This is between index 4 and 5.
# But since we only have 5 elements (indices 0-4), index 5 doesn't exist.
# Hmm, MATLAB's default quantile method (type 5) computes:
#   h = (n-1)*p + 1 = 4*0.9 + 1 = 4.6
#   If h is integer: x[h]
#   Else: x[floor(h)] + (h - floor(h)) * (x[ceil(h)] - x[floor(h)])
#   For 1-based indexing: h = 4.6, floor(h) = 4, ceil(h) = 5
#   x[4] + 0.6 * (x[5] - x[4]) = 4 + 0.6*(5-4) = 4.6

# Let me check with numpy
print("Expected: 4.6")

# Test with another array
x2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
print("numpy hazen 90th percentile:", np.percentile(x2, 90, method='hazen'))
# h = (6-1)*0.9 + 1 = 5.5
# x[5] + 0.5*(x[6]-x[5]) = 5 + 0.5*(6-5) = 5.5
print("Expected: 5.5")
