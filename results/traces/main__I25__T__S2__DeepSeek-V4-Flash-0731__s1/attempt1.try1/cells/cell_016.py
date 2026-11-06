
import numpy as np
print(np.__version__)
# Test hazen method
x = np.array([1, 2, 3, 4, 5])
print(np.percentile(x, 50, method='hazen'))
print(np.percentile(x, 90, method='hazen'))
