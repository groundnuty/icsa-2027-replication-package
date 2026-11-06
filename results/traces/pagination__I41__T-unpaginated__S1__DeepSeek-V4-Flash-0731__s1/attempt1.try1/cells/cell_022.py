
# Verify numpy's method='hazen' percentile computation
import numpy as np

# Test with a small example
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
p90_hazen = np.percentile(data, 90, method='hazen')
print(f"P90 (hazen): {p90_hazen}")

# Check what MATLAB would give for the same data
# MATLAB's quantile(v, 0.9) with default method (linear interpolation)
# For 10 data points, 90th percentile using linear interpolation:
# position = 0.9 * (10 - 1) + 1 = 9.1
# value = data[8] + 0.1 * (data[9] - data[8]) = 9 + 0.1 = 9.1
# But hazen uses: position = 0.5 + 0.9 * 10 = 9.5
# value = data[8] + 0.5 * (data[9] - data[8]) = 9.5
print(f"Expected hazen: 9.5")

# Check with NaN
data_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
p90_nan = np.nanpercentile(data_nan, 90, method='hazen')
print(f"P90 with NaN (hazen): {p90_nan}")
# With NaN removed: [1,2,4,5,6,7,8,9,10], n=9
# hazen: h = 0.5 + 0.9*9 = 8.6, so value between data[7]=9 and data[8]=10
# = 9 + 0.6*(10-9) = 9.6
print(f"Expected: 9.6")
