
import numpy as np

# Test numpy quantile with method='hazen'
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("P90 with hazen:", np.quantile(x, 0.9, method='hazen'))
print("P90 with linear:", np.quantile(x, 0.9, method='linear'))
print("P50 with hazen:", np.quantile(x, 0.5, method='hazen'))

# MATLAB default quantile (Hazen, type 5)
# For sorted x of length n, p-th quantile is at position (n*p + 0.5), interpolated
n = len(x)
p = 0.9
pos = n * p + 0.5  # Hazen: (k-0.5)/n = p => k = n*p + 0.5
print("Hazen position:", pos)
# pos = 4.5 + 0.5 = 5.0, so it's x[4] = 5.0
# Wait, position 5.0 in 1-indexed means element 5 = 5.0
# In 0-indexed: x[4] = 5.0
print("Expected (1-indexed position 5.0):", x[4])

# Let me verify numpy's hazen formula
# numpy hazen: h = (N-1)*p + 0.5? or h = (N)*p + 0.5?
# From numpy docs: h = (N-1)*p + 0.5
h = (n-1)*0.9 + 0.5
print("Numpy hazen h:", h)
# h = 4*0.9 + 0.5 = 3.6 + 0.5 = 4.1
# So it's between x[4] and x[5]? But we only have 5 elements (indices 0-4)
# Actually, h=4.1 means interpolate between x[4] and x[5] = 5.0 and beyond?
# Let me check what numpy actually does

# Try a simpler test
x2 = np.array([1.0, 2.0, 3.0, 4.0])
print("\nP50 of [1,2,3,4] with hazen:", np.quantile(x2, 0.5, method='hazen'))
print("P50 of [1,2,3,4] with linear:", np.quantile(x2, 0.5, method='linear'))
