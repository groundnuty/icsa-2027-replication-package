
import numpy as np
print("NumPy version:", np.__version__)

# Test hazen method
a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
q = np.nanquantile(a, 0.9, method='hazen')
print("Quantile 0.9 of [1,2,3,4,5] with hazen:", q)

# MATLAB quantile should give same result
# MATLAB's default is Type 5 (Hazen)
# For 5 data points, p=0.9: h = (N-1)*p + 1 = 4*0.9 + 1 = 4.6
# Since h is not an integer, interpolation: x_4 + (h-4)*(x_5 - x_4) = 4 + 0.6*1 = 4.6
print("Expected MATLAB result: 4.6")
