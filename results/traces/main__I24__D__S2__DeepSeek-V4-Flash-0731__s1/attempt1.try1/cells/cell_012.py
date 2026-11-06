
import numpy as np

# Verify nanquantile with hazen matches MATLAB's quantile ignoring NaN
x = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
print("nanquantile hazen 0.9:", np.nanquantile(x, 0.9, method='hazen'))

# Should be same as quantile of non-nan values
x_no_nan = np.array([1.0, 2.0, 4.0, 5.0])
print("quantile hazen 0.9:", np.quantile(x_no_nan, 0.9, method='hazen'))
