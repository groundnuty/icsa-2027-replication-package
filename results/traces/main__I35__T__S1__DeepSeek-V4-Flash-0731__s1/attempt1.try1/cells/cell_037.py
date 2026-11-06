
import numpy as np

# Test numpy hazen percentile
data = np.array([1, 2, 3, 4, 5])

# Test different percentiles
for p in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
    result = np.percentile(data, p, method='hazen')
    print(f"p={p}%: {result}")

# Compare with manual calculation
# Hazen method: p(k) = (k - 0.5) / n, k = 1..n
# For p=0.9 (90th percentile), we need to find which k
# (k - 0.5) / 5 = 0.9 => k = 5
# So the 90th percentile is the 5th value = 5

# For p=0.1 (10th percentile):
# (k - 0.5) / 5 = 0.1 => k = 1
# 10th percentile = 1st value = 1

# For p=0.5 (50th percentile):
# (k - 0.5) / 5 = 0.5 => k = 3
# 50th percentile = 3rd value = 3

# But numpy might interpolate when p falls between two k values
# For p=0.4:
# (k - 0.5)/5 = 0.4 => k = 2.5
# So we interpolate between k=2 (value 2) and k=3 (value 3)
# = 2 + (3-2) * 0.5 = 2.5

print("\nManual calculations:")
print(f"p=40%: expected 2.5, got {np.percentile(data, 40, method='hazen')}")

# MATLAB's quantile: let me check what it actually does
# MATLAB quantile(data, p) for p=0.9 with n=5:
# In MATLAB, quantile uses linear interpolation of the empirical CDF
# with plotting position p(k) = (k - 0.5) / n (type 5)
# For n=5, p=0.9:
# h = (n-1)*p + 1 = 4*0.9 + 1 = 4.6
# value = data[floor(4.6)] + (4.6 - floor(4.6)) * (data[ceil(4.6)] - data[floor(4.6)])
#      = data[4] + 0.6 * (data[5] - data[4])  [1-indexed]
#      = 4 + 0.6 * (5 - 4) = 4.6

# But numpy's hazen gives 5.0 for p=90%
# These are different! 
# MATLAB quantile with type 5: for n=5, p=0.9:
#   h = 1 + (n-1)*p = 1 + 4*0.9 = 4.6
#   value = x[4] + 0.6*(x[5]-x[4]) = 4 + 0.6 = 4.6

# numpy percentile method='hazen':
#   It uses the Hazen plotting position p(k) = (k-0.5)/n
#   and then interpolates
#   For p=0.9, n=5: (k-0.5)/5 = 0.9 => k = 5.0
#   If k is an integer, the value is just x[5] = 5.0

# So there's a discrepancy!
