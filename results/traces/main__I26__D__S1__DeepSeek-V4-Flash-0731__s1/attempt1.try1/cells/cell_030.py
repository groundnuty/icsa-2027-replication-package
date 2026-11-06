import numpy as np
# Check numpy version and available methods
print(np.__version__)
# Test hazen method
arr = np.array([1.0, 2.0, 3.0, 4.0])
try:
    q = np.percentile(arr, 90, method='hazen')
    print("hazen works:", q)
except Exception as e:
    print("Error:", e)
