
import numpy as np

# Check numpy version
print(f"NumPy version: {np.__version__}")

# Test with np.percentile
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("np.percentile with method='hazen':")
print(np.percentile(data, 90, method='hazen'))

# Test with np.quantile
print("np.quantile with method='hazen':")
print(np.quantile(data, 0.9, method='hazen'))

# Test with different methods
for method in ['linear', 'hazen', 'weibull', 'median_unbiased', 'normal_unbiased']:
    try:
        result = np.percentile(data, 90, method=method)
        print(f"  {method}: {result}")
    except Exception as e:
        print(f"  {method}: Error - {e}")
