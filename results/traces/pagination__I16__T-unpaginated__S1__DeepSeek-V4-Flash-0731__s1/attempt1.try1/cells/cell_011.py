
import numpy as np
print(np.__version__)
# Test method='hazen'
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print(np.quantile(x, 0.9, method='hazen'))
# Test nanquantile with method
x_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
print(np.nanquantile(x_nan, 0.9, method='hazen'))
