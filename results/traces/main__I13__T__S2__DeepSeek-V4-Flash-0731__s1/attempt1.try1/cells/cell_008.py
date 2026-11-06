
import numpy as np
print("Numpy version:", np.__version__)
# Test hazen method
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
p = np.percentile(data, 90, method='hazen')
print("90th percentile (hazen):", p)
p2 = np.percentile(data, 90, method='linear')
print("90th percentile (linear):", p2)
