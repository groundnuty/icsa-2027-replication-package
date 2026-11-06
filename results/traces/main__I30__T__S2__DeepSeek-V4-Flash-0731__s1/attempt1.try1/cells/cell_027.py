
import numpy as np

# Test Hazen percentile
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
p90_hazen = np.percentile(x, 90, method='hazen')
print(f"90th percentile (Hazen) of 1..10: {p90_hazen}")

# MATLAB quantile default should give same as Hazen (type 5)
# Let me verify with known example
# For data [1,2,3,4,5], 90th percentile with Hazen:
# n=5, p=0.9
# h = (n-1)*p + 1 = 4*0.9 + 1 = 4.6
# x_floor = x[4-1] = x[3] = 4 (0-indexed: floor(4.6)-1 = 3)
# x_ceil = x[5-1] = x[4] = 5 (0-indexed: ceil(4.6)-1 = 4)
# result = 4 + (4.6 - 4) * (5 - 4) = 4.6
x2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print(f"90th percentile (Hazen) of 1..5: {np.percentile(x2, 90, method='hazen')}")

# Check that we're using the correct method
print("Available methods:", np.percentile(np.array([1.0, 2.0, 3.0]), 50, method='hazen'))
print("MATLAB default (type 5):", np.percentile(np.array([1.0, 2.0, 3.0]), 50, method='hazen'))
