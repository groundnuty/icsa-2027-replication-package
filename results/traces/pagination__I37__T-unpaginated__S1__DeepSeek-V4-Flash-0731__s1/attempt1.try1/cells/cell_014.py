
import numpy as np
# Check available methods
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
for method in ['hazen', 'linear', 'lower', 'higher', 'midpoint', 'nearest', 'inverted_cdf', 'averaged_inverted_cdf', 'closest_observation', 'interpolated_inverted_cdf', 'hazen']:
    try:
        result = np.percentile(x, 90, method=method)
        print(f"{method}: {result}")
    except Exception as e:
        print(f"{method}: Error - {e}")
