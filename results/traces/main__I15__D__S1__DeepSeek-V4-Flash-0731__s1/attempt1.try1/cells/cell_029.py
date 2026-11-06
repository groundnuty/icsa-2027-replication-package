
import numpy as np

# Check np.quantile method='hazen'
x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)
print("Quantile with hazen:", np.quantile(x, 0.9, method='hazen'))

# Verify against MATLAB's quantile (Hyndman-Fan type 5)
# For n=10, p=0.9: h = (n-1)*p + 1 = 9*0.9 + 1 = 9.1
# x[floor(h)-1] + (h - floor(h)) * (x[ceil(h)-1] - x[floor(h)-1])
# = x[8] + 0.1 * (x[9] - x[8]) = 9 + 0.1 * (10-9) = 9.1
print("Expected MATLAB type 5: 9.1")
