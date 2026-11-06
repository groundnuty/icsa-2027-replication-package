
import numpy as np

# Check if np.nanpercentile supports method parameter
arr = np.array([[1.0, 2.0, np.nan], [3.0, 4.0, 5.0]])
try:
    result = np.nanpercentile(arr, 90, axis=0, method='hazen')
    print("np.nanpercentile with method='hazen' works:", result)
except Exception as e:
    print("Error:", e)

# Verify it matches manual filtering
arr2 = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
valid = arr2[np.isfinite(arr2)]
print("Manual hazen:", np.percentile(valid, 90, method='hazen'))
try:
    print("np.nanpercentile hazen:", np.nanpercentile(arr2, 90, method='hazen'))
except Exception as e:
    print("Error:", e)
