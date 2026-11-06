
import numpy as np

# Let me look at numpy's hazen method more carefully
# For [1,2,3,4,5], P90 with hazen gives 5.0
# Let me verify

x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("P90 with hazen:", np.quantile(x, 0.9, method='hazen'))
print("P90 with linear:", np.quantile(x, 0.9, method='linear'))

# numpy hazen: h = (N-1)*p + 0.5, where N is the sample size
# But wait, the formula might be different
# Let me check the numpy source/docs

# From numpy docs: method="hazen": 
#   h = (N - 1) * p + 0.5
#   Quantile = x[floor(h)] + (h - floor(h)) * (x[ceil(h)] - x[floor(h)])

# For N=5, p=0.9: h = 4*0.9 + 0.5 = 4.1
# floor(h) = 4, ceil(h) = 5 (out of bounds for 0-indexed array of size 5)
# Actually, numpy clamps: indices are in [0, N-1]
# So x[4] = 5, x[5] doesn't exist, so it's clamped to x[4]
# Quantile = x[4] + (4.1 - 4) * (x[4] - x[4]) = 5.0
# Actually no, ceil(4.1) = 5, which is out of bounds, so numpy must handle this

# Let me test with a slightly larger array
x3 = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
print("\nP90 of [10,20,30,40,50,60] with hazen:", np.quantile(x3, 0.9, method='hazen'))
# N=6, h = 5*0.9 + 0.5 = 5.0
# x[5] = 60
# So P90 = 60

print("P90 of [10,20,30,40,50,60] with linear:", np.quantile(x3, 0.9, method='linear'))
# linear: position = (N-1)*p = 5*0.9 = 4.5
# x[4] + 0.5*(x[5]-x[4]) = 50 + 0.5*10 = 55

# MATLAB default quantile for [10,20,30,40,50,60], p=0.9:
# Hazen type 5: position = N*p + 0.5 = 6*0.9 + 0.5 = 5.9
# Wait, that's different from numpy's formula
# MATLAB uses: q = (n-1)*p + 1 (in 1-indexed coordinates)?
# Actually, MATLAB type 5 (Hazen): 
#   h = (N-1)*p + 1  (1-indexed)
#   So for N=6, p=0.9: h = 5*0.9 + 1 = 5.5 (1-indexed)
#   This means it's between x[5] (0-indexed) and x[4] (0-indexed)?
#   No, 1-indexed position 5.5 is between element 5 and 6 (1-indexed)
#   = between 50 and 60 (0-indexed x[4] and x[5])
#   = 50 + 0.5*(60-50) = 55

# Wait, that doesn't match. Let me look this up more carefully.

# Actually, I think MATLAB's type 5 uses:
#   h = N*p + 0.5  (1-indexed)
#   For N=6, p=0.9: h = 5.4 + 0.5 = 5.9
#   Between element 5 and 6 (1-indexed) = x[4] and x[5] (0-indexed)
#   = 50 + 0.9*(60-50) = 59

# Hmm, let me check numpy's formula again.
# From numpy docs:
#   "hazen": Hazen's method (Hyndman & Fan, 1996)
#   h = (N-1) * p + 0.5
#   where N is the number of elements

# For N=6, p=0.9: h = 5*0.9 + 0.5 = 5.0
# x[5] = 60
# So numpy hazen gives 60

# Let me verify this matches MATLAB
# MATLAB quantile default (method 5, Hazen):
# From MATLAB docs: Q = quantile(X, p) returns quantiles using linear interpolation
# using the Hazen method
# For sorted X of length N, the p-th quantile is at position (N-1)*p + 1 (in 1-indexed)
# Hmm, let me check

# Actually, I recall from the Hyndman-Fan paper:
# Type 5: p_k = (k - 0.5) / n
# So for p = 0.9, we find k such that (k - 0.5) / n = p
# k - 0.5 = n*p
# k = n*p + 0.5
# This is in 1-indexed

# For N=6, p=0.9: k = 6*0.9 + 0.5 = 5.9
# 1-indexed position 5.9: between elements 5 and 6
# = x[4] + 0.9*(x[5]-x[4]) (0-indexed)
# = 50 + 0.9*10 = 59

# But numpy gives 60 with hazen for this case. Let me check again.
print("Let me test more carefully:")
x4 = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
print("numpy hazen P90:", np.quantile(x4, 0.9, method='hazen'))
print("numpy linear P90:", np.quantile(x4, 0.9, method='linear'))
print("numpy hazen P50:", np.quantile(x4, 0.5, method='hazen'))
