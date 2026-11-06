
import numpy as np
print(f"NumPy version: {np.__version__}")

# Test nanquantile with method='hazen'
data = np.array([[1.0, 2.0], [np.nan, 4.0], [3.0, 6.0]])
try:
    result = np.nanquantile(data, 0.9, axis=0, method='hazen')
    print(f"nanquantile with hazen: {result}")
except Exception as e:
    print(f"Error: {e}")
