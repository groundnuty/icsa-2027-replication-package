
import numpy as np

# Test with different methods
x = np.array([1.0, 2.0, 3.0, 4.0])
print("Hazen:", np.quantile(x, 0.9, method='hazen'))
print("Linear:", np.quantile(x, 0.9, method='linear'))
print("Lower:", np.quantile(x, 0.9, method='lower'))
print("Higher:", np.quantile(x, 0.9, method='higher'))
print("Midpoint:", np.quantile(x, 0.9, method='midpoint'))
print("Nearest:", np.quantile(x, 0.9, method='nearest'))
print("Weibull:", np.quantile(x, 0.9, method='weibull'))

# Check numpy hazen formula
# Hazen: h = (N-1)*p + 1
# For N=4, p=0.9: h = 3*0.9 + 1 = 3.7
# q = x[floor(3.7)-1] + (3.7 - floor(3.7)) * (x[ceil(3.7)-1] - x[floor(3.7)-1])
# In 0-indexed: q = x[2] + 0.7 * (x[3] - x[2]) = 3 + 0.7 = 3.7

# But numpy gives 4.0. Let me investigate.

# Check MATLAB's behavior
# MATLAB quantile([1 2 3 4], 0.9) should give 3.7
# But maybe numpy's hazen uses a different formula?
# Let me check numpy's source code or docs

# Let me test with sorted data to understand
y = np.array([1.0, 2.0, 3.0])
print("\n[1,2,3] p=0.9 hazen:", np.quantile(y, 0.9, method='hazen'))
# h = 2*0.9 + 1 = 2.8
# q = x[1] + 0.8 * (x[2] - x[1]) = 2 + 0.8 * 1 = 2.8
# Expected: 2.8

z = np.array([1.0, 2.0])
print("[1,2] p=0.9 hazen:", np.quantile(z, 0.9, method='hazen'))
# h = 1*0.9 + 1 = 1.9
# q = x[0] + 0.9 * (x[1] - x[0]) = 1 + 0.9 * 1 = 1.9
# Expected: 1.9
