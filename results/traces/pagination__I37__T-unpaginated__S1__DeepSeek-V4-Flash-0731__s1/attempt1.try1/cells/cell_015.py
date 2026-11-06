
import numpy as np
x = np.array([1.0, np.nan, 2.0, 3.0, 4.0, 5.0])
try:
    result = np.nanpercentile(x, 90, method='hazen')
    print(f"nanpercentile with hazen: {result}")
except Exception as e:
    print(f"Error: {e}")
    
# Also try with nan_policy
try:
    result = np.nanpercentile(x, 90, method='hazen')
    print(f"nanpercentile with hazen (with nan): {result}")
except Exception as e:
    print(f"Error: {e}")
