
import numpy as np
print(np.__version__)
# Test hazen method
x = np.array([1.0, 2.0, 3.0, 4.0])
print(np.percentile(x, 90, method='hazen'))
# Test with NaN
x2 = np.array([1.0, np.nan, 3.0, 4.0])
print(np.nanpercentile(x2, 90, method='hazen'))
