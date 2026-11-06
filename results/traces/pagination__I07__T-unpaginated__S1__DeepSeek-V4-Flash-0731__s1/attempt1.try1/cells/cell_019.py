
import numpy as np

# Test numpy's hazen method
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
p90 = np.percentile(data, 90, method='hazen')
print(f"90th percentile (hazen): {p90}")

# MATLAB quantile with default method (type 7) for comparison
p90_linear = np.percentile(data, 90, method='linear')
print(f"90th percentile (linear): {p90_linear}")

# Let me check what numpy version we have
print(f"NumPy version: {np.__version__}")

# Test with NaN
data_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
valid = data_nan[~np.isnan(data_nan)]
p90_nan = np.percentile(valid, 90, method='hazen')
print(f"90th percentile (hazen, ignoring NaN): {p90_nan}")
