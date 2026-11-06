
import numpy as np

# Test with a small array
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
q = np.quantile(data, 0.9, method='hazen')
print(f"numpy hazen: {q}")

# MATLAB default quantile for this data
# MATLAB sorts data, then uses linear interpolation at position (n-1)*p + 1
# Actually, MATLAB documentation says:
# "For the default method, Q = quantile(A,p) uses linear interpolation."
# MATLAB's default is actually Hyndman-Fan type 5 for the "linear" method.

# Let me verify what the MATLAB default gives
# MATLAB: quantile([1 2 3 4 5], 0.9) = ?
# MATLAB's linear interpolation: at position (n-1)*p + 1 = 4*0.9 + 1 = 4.6
# The value at position 4.6 (1-indexed) = value[3] + 0.6 * (value[4] - value[3]) 
# = 4 + 0.6 * (5 - 4) = 4.6

# numpy hazen: method='hazen' gives the same result?
# Hazen: (n+1)p-th value with linear interpolation
# (5+1)*0.9 = 5.4
# value at position 5.4 = value[4] + 0.4 * (value[5] - value[4])... 
# Actually in numpy, the quantile uses the formula:
# index = (n+1)*p - 1 (0-indexed) for hazen method
# = 6*0.9 - 1 = 4.4
# value = data[4] + 0.4 * (data[5] - data[4]) but data has indices 0-4, so data[4]=5
# Hmm, let me just run it.

data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
for p in [0.25, 0.5, 0.9]:
    q_hazen = np.quantile(data, p, method='hazen')
    q_linear = np.quantile(data, p, method='linear')
    print(f"p={p}: hazen={q_hazen}, linear={q_linear}")

# MATLAB's default quantile uses method "linear" according to some sources
# or the Hazen method. Let me check what MATLAB actually does.
# MATLAB docs say: "quantile(A,p) returns quantiles of elements in input data A for 
# the cumulative probability or probabilities p in the interval [0,1]."
# "For the method 'linear' (the default), quantile uses linear interpolation 
# with triangular weights."

# Actually, MATLAB's default is described as: 
# For a sample of size n, the p-quantile is computed using:
# j = floor(np) + 1, gamma = np - floor(np) (if np is not integer)
# x_hat = x_j + gamma * (x_{j+1} - x_j)
# This is actually the same as numpy's method='linear'

# But the task says "MATLAB's quantile does by default, which is numpy's method='hazen'"
# So numpy's hazen should match MATLAB's default

# Let me check: for [1,2,3,4,5], p=0.9:
# MATLAB: j = floor(5*0.9) = 4, gamma = 4.5 - 4 = 0.5
# Wait, that doesn't work either. Let me think again.

# Actually, MATLAB's default quantile uses this algorithm:
# For p-quantile, compute index i = (n-1)*p + 1 (1-indexed)
# For n=5, p=0.9: i = 4*0.9 + 1 = 4.6
# floor(i) = 4, frac = 0.6
# result = x(4) + frac * (x(5) - x(4)) = 4 + 0.6*(5-4) = 4.6

# numpy's hazen: index = (n+1)*p - 1 (0-indexed)
# For n=5, p=0.9: index = 6*0.9 - 1 = 4.4
# floor = 4, frac = 0.4
# result = x(4) + frac * (x(5)-x(4))... but 0-indexed, x(4)=5, and x(5) is out of bounds
# Hmm, that doesn't seem right either.

# Let me just run it:
print()
q = np.quantile(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), 0.9, method='hazen')
print(f"numpy hazen 0.9 of [1,2,3,4,5]: {q}")
