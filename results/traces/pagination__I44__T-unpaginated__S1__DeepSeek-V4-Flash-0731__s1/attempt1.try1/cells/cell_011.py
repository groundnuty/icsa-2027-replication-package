import numpy as np

# Check numpy quantile methods
try:
    q = np.quantile([1,2,3,4,5], 0.9, method='hazen')
    print(f"Hazen: {q}")
except Exception as e:
    print(f"Error: {e}")

# Check what methods are available
import numpy as np
methods = ['linear', 'lower', 'higher', 'midpoint', 'nearest', 'inverted_cdf', 'averaged_inverted_cdf', 'closest_observation', 'interpolated_inverted_cdf', 'hazen', 'weibull', 'median_unbiased', 'normal_unbiased']
for m in methods:
    try:
        q = np.quantile([1,2,3,4,5], 0.9, method=m)
        print(f"{m}: {q}")
    except Exception as e:
        print(f"{m}: Error - {e}")
