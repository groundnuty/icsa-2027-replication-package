
import numpy as np
# Check nanpercentile with method
x = np.array([[1.0, 2.0, 3.0], [np.nan, 5.0, 6.0], [7.0, 8.0, np.nan]])
try:
    result = np.nanpercentile(x, 90, axis=0, method='hazen')
    print("nanpercentile with hazen:", result)
except Exception as e:
    print("Error:", e)

# Check percentile with method='hazen' and NaN values
try:
    result = np.percentile(x, 90, axis=0, method='hazen')
    print("percentile with hazen (no NaN handling):", result)
except Exception as e:
    print("Error:", e)
