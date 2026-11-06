
import numpy as np
print("Numpy version:", np.__version__)

# Test hazen with NaN
x = np.array([1.0, np.nan, 2.0, 3.0, 4.0, 5.0])
print("nanpercentile hazen:", np.nanpercentile(x, 90, method='hazen'))
print("nanmean:", np.nanmean(x))

# Verify hazen matches Hyndman-Fan type 5
# Type 5: p[k] = (k - 0.5) / n
# For p=0.9, n=5 valid values (1,2,3,4,5): k = 0.9*5 + 0.5 = 5.0
# So the 90th percentile should be x[4] = 5 (0-indexed)
x2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
print("hazen p90:", np.percentile(x2, 90, method='hazen'))
print("Expected: 5.0")
