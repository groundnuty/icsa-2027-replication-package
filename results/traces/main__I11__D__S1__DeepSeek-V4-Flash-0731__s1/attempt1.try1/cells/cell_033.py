
import numpy as np

# Test numpy's hazen method
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
q = np.quantile(data, 0.9, method='hazen')
print(f"numpy quantile with hazen: {q}")

# Verify with MATLAB-style calculation
# MATLAB default quantile uses linear interpolation
# Hyndman-Fan type 5 (Hazen): h = (N-1)*p + 1
# For N=5, p=0.9: h = 4*0.9 + 1 = 4.6
# Q = x_floor(4.6) + 0.6*(x_ceil(4.6) - x_floor(4.6)) = 4 + 0.6*(5-4) = 4.6
print(f"Expected: 4.6")
