
import numpy as np

# Compare with MATLAB-style
# MATLAB quantile uses linear interpolation (type 5 = hazen)
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("hazen 0.9:", np.quantile(x, 0.9, method='hazen'))

# Test with NaN
x2 = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
print("hazen 0.9 with nan:", np.quantile(x2, 0.9, method='hazen'))
print("nanquantile hazen 0.9:", np.nanquantile(x2, 0.9, method='hazen'))
