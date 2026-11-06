
import numpy as np

# Test numpy percentile with different methods
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

print("Method 'linear':", np.percentile(x, 90, method='linear'))
print("Method 'hazen':", np.percentile(x, 90, method='hazen'))
print("Method 'inverted_cdf':", np.percentile(x, 90, method='inverted_cdf'))

# MATLAB default quantile should be linear interpolation
# For x = [1,2,3,4,5], p=0.9
# position = (n-1)*p + 1 = 4*0.9+1 = 4.6 (1-based)
# value = x[floor(4.6)-1] + 0.6*(x[ceil(4.6)-1]-x[floor(4.6)-1])
# = x[3] + 0.6*(x[4]-x[3]) = 4 + 0.6 = 4.6
print("Expected MATLAB default: 4.6")

# Check the hazen method in detail
# h = (n + 0.5)*p + 0.5
n = len(x)
p = 0.9
h = (n + 0.5) * p + 0.5
print(f"hazen h = {h}")
# h = 5.45, which is between 5 and 6 (1-based)
# But since there are only 5 elements, what happens?
# The numpy implementation must handle this differently

# Let me check with a larger array
x2 = np.arange(1, 21, dtype=float)  # 1 to 20
print("\nFor x = 1 to 20:")
print("numpy hazen 90th:", np.percentile(x2, 90, method='hazen'))
# h = (20+0.5)*0.9+0.5 = 18.45+0.5 = 18.95
# Between 18 and 19 (1-based), i.e., between x[17]=18 and x[18]=19
# value = 18 + 0.95*(19-18) = 18.95
print("Expected: 18.95")

# Test with numpy linear
print("numpy linear 90th:", np.percentile(x2, 90, method='linear'))
# h = (20-1)*0.9+1 = 18.1
# Between x[17]=18 and x[18]=19
# value = 18 + 0.1*(19-18) = 18.1
print("Expected: 18.1")
