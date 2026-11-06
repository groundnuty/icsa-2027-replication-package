
import numpy as np

# Test Hazen quantile
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
q = np.quantile(data, 0.9, method='hazen')
print(f"Hazen 90th percentile of [1,2,3,4,5]: {q}")

# MATLAB quantile default for 90th percentile of 1:5
# MATLAB uses linear interpolation between order statistics
# For p=0.9 and n=5: position = (n-1)*p + 1 = 4.6
# So it interpolates between the 4th and 5th values
# 4 + 0.6*(5-4) = 4.6
# But Hazen: position = (n+0.5)*p + 0.5? No...
# Let me just verify against numpy's implementation
print("Expected for [1,2,3,4,5] q90:", 4.6)

# Verify with a specific pool size
np.random.seed(42)
data2 = np.random.randn(121)
q2 = np.quantile(data2, 0.9, method='hazen')
print(f"Hazen quantile for 121 random values: {q2}")
