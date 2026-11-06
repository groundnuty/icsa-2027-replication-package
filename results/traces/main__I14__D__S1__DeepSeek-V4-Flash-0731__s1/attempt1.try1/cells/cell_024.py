
import numpy as np

# Let me test various methods for the 90th percentile of [1,2,3,4]
x = np.array([1., 2., 3., 4.])

for method in ['hazen', 'linear', 'lower', 'higher', 'midpoint', 'nearest', 'weibull', 'inverted_cdf', 'averaged_inverted_cdf', 'closest_observation', 'interpolated_inverted_cdf']:
    try:
        q = np.percentile(x, 90, method=method)
        print(f"{method}: {q}")
    except Exception as e:
        print(f"{method}: ERROR {e}")
