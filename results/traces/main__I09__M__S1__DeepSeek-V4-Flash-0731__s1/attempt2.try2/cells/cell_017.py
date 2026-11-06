
import numpy as np
print(np.__version__)
# Check if nanquantile supports method parameter
x = np.array([[1.0, 2.0], [np.nan, 4.0]])
try:
    result = np.nanquantile(x, 0.9, axis=0, method='hazen')
    print(result)
except Exception as e:
    print(f"Error: {e}")
