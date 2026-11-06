
import numpy as np

# Test different numpy quantile methods
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

methods = ['linear', 'lower', 'higher', 'midpoint', 'nearest', 'hazen', 'weibull', 'median_unbiased', 'normal_unbiased']
for m in methods:
    try:
        q = np.quantile(data, 0.9, method=m)
        print(f"method={m}: q(0.9) = {q}")
    except Exception as e:
        print(f"method={m}: error: {e}")

# Also check the default
print(f"Default: {np.quantile(data, 0.9)}")
