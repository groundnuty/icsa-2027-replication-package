import numpy as np

# Verify numpy's hazen method
test_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
q = np.quantile(test_data, 0.9, method='hazen')
print("Hazen quantile(0.9) of [1,2,3,4,5]:", q)
# MATLAB default should give the same

# Let me check what hazen does
# Hazen: Q(p) = x_{floor(h)} + (h - floor(h)) * (x_{ceil(h)} - x_{floor(h)})
# where h = (N - 1) * p + 1  (or similar)
# For N=5, p=0.9: h = 4 * 0.9 + 1 = 4.6
# x_4 = 5, x_5 = 5 (h goes up to 4.6, so x_floor(4.6)=x_4=5, x_ceil(4.6)=x_5... 
# Actually, 1-based: x_floor(4.6) = x_4 = 4, x_ceil(4.6) = x_5 = 5
# Q = 4 + 0.6 * (5 - 4) = 4.6

# Let me verify numpy gives 4.6
print("Expected ~4.6, got:", q)
