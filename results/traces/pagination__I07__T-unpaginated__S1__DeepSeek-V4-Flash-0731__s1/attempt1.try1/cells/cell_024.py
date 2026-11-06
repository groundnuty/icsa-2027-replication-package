
import numpy as np

# Test nanpercentile with method='hazen'
x = np.array([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
              [2.0, 3.0, np.nan, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0],
              [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]])
# Compute nanpercentile along axis=1
result = np.nanpercentile(x, 90, axis=1, method='hazen')
print(f"nanpercentile result: {result}")
print(f"Expected for row 0: {np.percentile(np.arange(1,11), 90, method='hazen')}")
print(f"Expected for row 1: {np.percentile(np.array([2,3,5,6,7,8,9,10,11]), 90, method='hazen')}")
print(f"Expected for row 2 (all NaN): NaN")

# Test nanmean along axis=1
mean_result = np.nanmean(x, axis=1)
print(f"\nnanmean result: {mean_result}")
print(f"Expected for row 0: {np.mean(np.arange(1,11))}")
print(f"Expected for row 1: {np.mean(np.array([2,3,5,6,7,8,9,10,11]))}")

# Verify nanpercentile gives same as manual filtering
# For row 0
row0 = x[0]
valid0 = row0[~np.isnan(row0)]
manual_p0 = np.percentile(valid0, 90, method='hazen')
print(f"\nRow 0: nanpercentile={result[0]}, manual={manual_p0}")
assert abs(result[0] - manual_p0) < 1e-10

# For row 1
row1 = x[1]
valid1 = row1[~np.isnan(row1)]
manual_p1 = np.percentile(valid1, 90, method='hazen')
print(f"Row 1: nanpercentile={result[1]}, manual={manual_p1}")
assert abs(result[1] - manual_p1) < 1e-10

print("\nAll tests passed!")
