
import numpy as np

# Test Hazen percentile
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
p90 = np.percentile(data, 90, method='hazen')
print("Hazen 90th percentile of [1,2,3,4,5]:", p90)

# MATLAB's quantile default is the same as numpy's method="linear" 
# Wait, the task says "MATLAB's quantile does by default, which is numpy's method='hazen'"
# Let me verify

# MATLAB quantile default (type 5 / Hazen)
# For 90th percentile with 5 values:
# p = 0.9, n = 5
# Position: (n+1)*p = 6*0.9 = 5.4
# hmm, let me think about this

# Hyndman-Fan type 5 (Hazen): 
# Q(p) = x_(⌊(n+1)p⌋) + ((n+1)p - ⌊(n+1)p⌋)(x_(⌊(n+1)p⌋+1) - x_(⌊(n+1)p⌋))
# For n=5, p=0.9: (n+1)p = 5.4
# x_(5) = 5, x_(6) = ... hmm

# Actually, Hazen uses: h = (N-1)*p + 1 (or (N+1)*p in some formulations)
# Let me just verify what numpy gives

# For numpy method="hazen": 
# h = (N-1)*p + 1 (using 0-indexed positions, then maps to data)
# Actually, I think numpy's implementation is standard.

data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
for method in ['hazen', 'linear', 'weibull']:
    print(f"{method}: {np.percentile(data, 90, method=method)}")

# MATLAB quantile by default: 
# q = 0.9, n = 5
# MATLAB uses: h = (n-1)*q + 1 = 4.6, x = x_floor + (h - floor)*(x_ceil - x_floor)
# = x_4 + 0.6*(x_5 - x_4) = 4 + 0.6*(5-4) = 4.6
# This is the Hazen method
print("\nMATLAB default quantile(1:5, 0.9) =", 4.6)
