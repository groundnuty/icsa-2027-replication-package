
import numpy as np

# Test Hazen quantile
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
q = np.quantile(data, 0.9, method='hazen')
print("Hazen 90th percentile:", q)

# Test with NaN
data_nan = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
q_nan = np.nanquantile(data_nan, 0.9, method='hazen')
print("Hazen 90th percentile (with NaN):", q_nan)

# Verify Hazen formula
# Hyndman-Fan type 5: h = (N+1)*p
# For N=5, p=0.9: h = 6*0.9 = 5.4
# Since h > N, it's capped at N: value = data[4] = 5.0
# Wait, that doesn't seem right. Let me look up the formula.
# Type 5 (Hazen): Q(p) = x[floor(h)] + (h - floor(h)) * (x[floor(h)+1] - x[floor(h)])
# where h = (N+1)*p
# For N=5, p=0.9: h = 5.4
# floor(h) = 5, but 1-indexed so data[5] = 5.0 (last element)
# h - floor(h) = 0.4, but floor(h)+1 = 6 which is out of bounds
# In practice, Hazen caps h at N: h = min(h, N)
# So h = 5, Q = data[4] = 5.0

# Let me test with a different example
data2 = np.array([10.0, 20.0, 30.0, 40.0])
q2 = np.quantile(data2, 0.9, method='hazen')
print("Hazen 90th percentile of [10,20,30,40]:", q2)
# N=4, h = (N+1)*0.9 = 4.5, capped at 4, Q = data[3] = 40.0

# Let me also verify with another test
data3 = np.array([1.0, 2.0, 3.0, 4.0])
q3 = np.quantile(data3, 0.5, method='hazen')
print("Hazen 50th percentile of [1,2,3,4]:", q3)
# N=4, h = (N+1)*0.5 = 2.5
# Q = x[1] + 0.5*(x[2]-x[1]) = 2 + 0.5*1 = 2.5 (0-indexed: data[1] + 0.5*(data[2]-data[1]))
# = 2 + 0.5*1 = 2.5

# Compare with MATLAB
# MATLAB default quantile for [1,2,3,4], 0.5:
# n=4, position = (n-1)*0.5 + 1 = 2.5
# interpolate between 2nd and 3rd: 2.5
# So MATLAB would give 2.5 as well

# Let me check the spec: "MATLAB's quantile does by default, which is numpy's method='hazen'"
# This seems to suggest MATLAB's default is the Hazen method, but I thought MATLAB uses linear interpolation (type 7) by default.

# Actually, I just realized that newer MATLAB versions may have changed. Let me not worry about this - I'll follow the spec exactly and use method='hazen'.

print("np.quantile methods available:", np.quantile(np.array([1.,2.,3.]), 0.5, method='hazen'))
