
import numpy as np
# Test hazen method
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print(np.percentile(x, 90, method='hazen'))
print(np.nanpercentile(x, 90, method='hazen'))
