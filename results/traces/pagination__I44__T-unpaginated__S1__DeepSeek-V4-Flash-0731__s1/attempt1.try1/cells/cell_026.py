import numpy as np

# Test nanquantile with hazen method
data = np.array([1.0, 2.0, 3.0, np.nan, 4.0, 5.0, 6.0])
# Without NaN: quantile of [1,2,3,4,5,6] at 0.9 using hazen
q = np.quantile(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), 0.9, method='hazen')
print(f"Quantile 0.9 of [1,2,3,4,5,6] (hazen): {q}")

# With NaN (should give same result)
q_nan = np.nanquantile(data, 0.9, method='hazen')
print(f"Nanquantile 0.9 (hazen): {q_nan}")

# Also check with MATLAB-style computation
# MATLAB quantile uses linear interpolation between closest ranks
# For 90th percentile of 6 values:
# Position = 0.9 * (6-1) + 1 = 5.5 (in MATLAB's 1-based indexing)
# This corresponds to interpolation between the 5th and 6th smallest values
# In 0-based: position 4.5, so value = data[4] + 0.5*(data[5] - data[4])
sorted_data = np.sort(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]))
matlab_q = sorted_data[4] + 0.5 * (sorted_data[5] - sorted_data[4])
print(f"MATLAB-style 0.9: {matlab_q}")
print(f"Matches: {np.isclose(q, matlab_q)}")
