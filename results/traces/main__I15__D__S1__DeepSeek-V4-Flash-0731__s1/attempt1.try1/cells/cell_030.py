
import numpy as np

x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)

# Check what numpy's hazen computes
q = np.quantile(x, 0.9, method='hazen')
print("numpy hazen:", q)

# Verify: h = (n - 1/2) * p + 1/2 = 9.5 * 0.9 + 0.5 = 8.55 + 0.5 = 9.05
n = len(x)
p = 0.9
h = (n - 1/2) * p + 1/2
print("h =", h)

# Q = x[floor(h)-1] + (h-floor(h))*(x[ceil(h)-1]-x[floor(h)-1])
# (1-indexed) x(9) = 9, x(10) = 10
# Q = 9 + 0.05 * (10 - 9) = 9.05
print("Expected:", 9 + 0.05 * (10 - 9))

# But numpy gives 9.5? Let me check with the linear method
print("numpy linear:", np.quantile(x, 0.9, method='linear'))
# Linear: h = (n-1)*p + 1 = 9*0.9+1 = 9.1
# Q = x(9) + 0.1*(x(10)-x(9)) = 9 + 0.1 = 9.1
