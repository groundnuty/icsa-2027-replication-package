
import numpy as np

# Test nanpercentile with method='hazen'
data = np.array([1.0, 2.0, 3.0, np.nan, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
try:
    p = np.nanpercentile(data, 90, method='hazen')
    print("nanpercentile with hazen:", p)
except Exception as e:
    print("Error:", e)

# Test regular percentile with NaN
try:
    p = np.percentile(data, 90, method='hazen')
    print("percentile with hazen and NaN:", p)
except Exception as e:
    print("Error:", e)

# Test nanmean
m = np.nanmean(data)
print("nanmean:", m)
