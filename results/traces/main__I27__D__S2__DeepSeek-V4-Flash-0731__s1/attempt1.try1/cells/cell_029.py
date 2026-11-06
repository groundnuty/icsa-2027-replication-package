
import numpy as np

data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

methods = ['linear', 'lower', 'higher', 'nearest', 'midpoint', 'nearest_even',
           'inverted_cdf', 'averaged_inverted_cdf', 'closest_observation',
           'interpolated_inverted_cdf', 'hazen', 'weibull', 'median_unbiased',
           'normal_unbiased']

for m in methods:
    try:
        result = np.percentile(data, 90, method=m)
        print(f"{m}: {result}")
    except ValueError as e:
        print(f"{m}: ERROR - {e}")

print("\nnumpy version:", np.__version__)

# Let me check MATLAB's default quantile result
# MATLAB quantile([1:10], 0.9) with default method
# Method 5 (Hazen): h = (n+1)*p = 11*0.9 = 9.9
# Position 9.9 means between the 9th and 10th values: 9 + 0.9*(10-9) = 9.9

# numpy method='interpolated_inverted_cdf' might be what I'm thinking of
# Let me check the numpy docs for hazen more carefully
