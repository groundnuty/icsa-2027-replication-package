
import numpy as np

# Verify hazen percentile
data = np.array([1, 2, 3, 4, 5])
# numpy hazen
p = np.percentile(data, 90, method='hazen')
print(f"Hazen 90th percentile of [1,2,3,4,5]: {p}")

# Verify with MATLAB
# In MATLAB, quantile(data, 0.9) uses type 5 (Hazen) by default
# For n=5, type 5: h = (n-1)*p + 1 = 4*0.9 + 1 = 4.6
# So value at position 4.6 = data[3] + 0.6*(data[4] - data[3]) = 4 + 0.6*1 = 4.6
print(f"Expected: 4.6")

# Verify with NaN values
data2 = np.array([1, np.nan, 2, 3, 4, 5])
p2 = np.percentile(data2[~np.isnan(data2)], 90, method='hazen')
print(f"Hazen 90th percentile ignoring NaN: {p2}")

# Verify mean ignoring NaN
m = np.nanmean(data2)
print(f"Mean ignoring NaN: {m}")
