
import numpy as np

# Test nanpercentile on 3D array
data = np.random.rand(10, 3, 4) * 10
data[0, 0, 0] = np.nan
data[5, 2, 3] = np.nan
result = np.nanpercentile(data, 90, axis=0, method='hazen')
print("Result shape:", result.shape)
print(result[0, 0], "should not be NaN (first value was NaN)")
print(result[2, 3], "should not be NaN (a value was NaN)")

# Test nanmean on 3D array
mean_result = np.nanmean(data, axis=0)
print("Mean result shape:", mean_result.shape)
