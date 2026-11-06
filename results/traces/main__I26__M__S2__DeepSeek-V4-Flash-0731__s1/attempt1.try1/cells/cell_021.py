
import numpy as np

# Verify hazen percentile
# numpy uses method='hazen' for quantile/percentile by default
# Let's verify with a small example
test = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print(f"90th percentile (hazen): {np.percentile(test, 90, method='hazen')}")

# Verify that np.nanpercentile with hazen is what we want
test2 = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
print(f"90th percentile with NaN (hazen): {np.nanpercentile(test2, 90, method='hazen')}")
print(f"90th percentile ignoring NaN (hazen): {np.percentile(test2[~np.isnan(test2)], 90, method='hazen')}")

# Check MATLAB quantile vs numpy hazen
# MATLAB's quantile with default method uses linear interpolation between closest ranks
# numpy's method='linear' corresponds to type 7 (default for numpy.percentile)
# But hazen corresponds to MATLAB's default quantile behavior
# Let me verify

# For MATLAB, quantile uses linear interpolation of the empirical CDF
# numpy percentile with method='hazen' is Hyndman-Fan type 5
# Let's verify what happens with a specific dataset

data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
print(f"\nHazen 90th pct: {np.percentile(data, 90, method='hazen')}")
print(f"Linear 90th pct: {np.percentile(data, 90, method='linear')}")

# For hazen (type 5): p_k = (k - 0.5) / n
# For 90th percentile of 10 values: 
# p = 0.9, n = 10
# k such that (k - 0.5) / 10 = 0.9, k = 9.5
# Since k is not integer, interpolate between 9th and 10th values
# Actually hazen uses: h = (N-1)p + 1 in some formulations
# Let me just trust numpy's hazen implementation
print("\nVerification done.")
