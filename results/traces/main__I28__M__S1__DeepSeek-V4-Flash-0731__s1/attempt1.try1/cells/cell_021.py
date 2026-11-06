
import numpy as np
print("numpy version:", np.__version__)
# Test hazen percentile
arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("90th percentile (hazen):", np.percentile(arr, 90, method='hazen'))
# Test with NaN
arr_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
# Check if percentile ignores NaN (it doesn't by default)
try:
    print("90th percentile with NaN (hazen):", np.percentile(arr_nan, 90, method='hazen'))
except Exception as e:
    print("Error:", e)
# Verify by filtering NaN manually
arr_valid = arr_nan[np.isfinite(arr_nan)]
print("90th percentile filtered (hazen):", np.percentile(arr_valid, 90, method='hazen'))
