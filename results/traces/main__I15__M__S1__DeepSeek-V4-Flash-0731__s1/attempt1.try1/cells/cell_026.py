import numpy as np

# Verify numpy's hazen method matches MATLAB's quantile
# MATLAB quantile uses linear interpolation
# numpy method='hazen' uses the formula: for p-quantile, index = (n-1)*p (using Hazen)
# Actually, let me check what MATLAB's default quantile does vs numpy's method='hazen'

# MATLAB's quantile uses the same approach as numpy's method='linear' 
# (which is Hyndman-Fan type 7), not method='hazen' (type 5).

# Wait, the task says: "computed as MATLAB's quantile does by default, 
# which is numpy's method='hazen' (Hyndman–Fan type 5)"

# Let me verify this claim. MATLAB's default quantile algorithm:
# For n elements, the p-th quantile is at position (n-1)*p + 1 (1-indexed)
# with linear interpolation.
# This is the same as Hyndman-Fan type 7 (numpy method='linear').

# numpy method='hazen' (type 5): position = n*p + 0.5

# Actually, let me just trust the task's description and use method='hazen'

# Test with a simple example
data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
p90_hazen = np.percentile(data, 90, method='hazen')
p90_linear = np.percentile(data, 90, method='linear')
print(f"90th percentile (hazen): {p90_hazen}")
print(f"90th percentile (linear): {p90_linear}")

# MATLAB: for n=10, p=0.9, position = (n-1)*0.9 + 1 = 9.1
# So value = data[8] + 0.1*(data[9]-data[8]) = 9 + 0.1*1 = 9.1
# numpy linear also gives 9.1

# numpy hazen: position = n*0.9 + 0.5 = 9.5, value = 9 + 0.5*(10-9)/1 ... 
# Actually, hazen uses position = n*p + 0.5 (0-indexed in some formulations)
print(f"Hazen formula check: should be around 9.45 or so")
