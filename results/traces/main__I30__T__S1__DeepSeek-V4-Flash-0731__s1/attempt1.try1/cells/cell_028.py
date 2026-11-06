
import numpy as np
# Check numpy version
print(np.__version__)
# Test hazen method
x = np.array([1, 2, 3, 4, 5])
print(np.quantile(x, 0.9, method='hazen'))
print(np.quantile(x, 0.9))
