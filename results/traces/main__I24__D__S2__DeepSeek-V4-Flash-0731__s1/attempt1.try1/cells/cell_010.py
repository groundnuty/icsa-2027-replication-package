
import numpy as np
print("numpy version:", np.__version__)

# Test hazen quantile
x = np.array([1.0, 2.0, 3.0, 4.0])
print(np.quantile(x, 0.9, method='hazen'))
print(np.quantile(x, 0.9))
