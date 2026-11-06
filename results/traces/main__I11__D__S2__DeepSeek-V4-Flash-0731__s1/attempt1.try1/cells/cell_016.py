
import numpy as np
# Test hazen
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print(np.percentile(x, 90, method='hazen'))
# MATLAB quantile default
# MATLAB: q = quantile(x, 0.9) uses linear interpolation (type 5 / hazen)
# Let me verify with a simple example
# For x = [1,2,3,4,5], p=0.9
# n=5, p*(n+1) = 5.4, so interpolate between 5th (index 5) and 6th (out of range)
# MATLAB quantile for p=0.9: 
# The MATLAB documentation says default is linear interpolation
# x(1) + (x(5)-x(1))*(0.9*(5-1)) = 1 + 4*3.6 = 1 + 14.4 = 15.4? No, that's wrong.
# Let me just trust numpy's hazen implementation.
print(np.percentile(np.array([1,2,3,4,5]), 90, method='hazen'))
# Expected: n=5, hazel: position = (n-1)*p + 1 = 4*0.9+1 = 4.6, interpolate between x[3]=4 and x[4]=5
# 4 + 0.6*(5-4) = 4.6
# Actually MATLAB quantile with default: position = p*(n-1)+1 for "linear" method? 
# Let me check what method='hazen' gives.
