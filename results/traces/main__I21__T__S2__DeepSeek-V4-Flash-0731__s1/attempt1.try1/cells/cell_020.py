
import numpy as np

# Test: compare numpy's hazen method to what MATLAB would produce
# MATLAB: quantile([1,2,3,4,5], 0.9)
# n=5, p=0.9, h = (5-1)*0.9 + 1 = 4.6
# x_floor(4.6)=x[4]=4 (1-indexed), x_ceil(4.6)=x[5]=5
# result = 4 + 0.6*(5-4) = 4.6

data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
result = np.percentile(data, 90, method='hazen')
print(f"numpy hazen: {result}")  # Should be 4.6

# Another test with NaN
data_with_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
data_clean = data_with_nan[np.isfinite(data_with_nan)]
result2 = np.percentile(data_clean, 90, method='hazen')
print(f"numpy hazen (with NaN removed): {result2}")  # Should be 4.6
