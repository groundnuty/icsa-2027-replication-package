
import numpy as np

# Test np.nanpercentile with method parameter and axis
data = np.array([
    [[1.0, 2.0, 3.0], [4.0, 5.0, np.nan]],
    [[6.0, 7.0, 8.0], [9.0, 10.0, 11.0]],
    [[12.0, 13.0, np.nan], [14.0, 15.0, 16.0]],
])
print("data shape:", data.shape)

# Compute percentile along axis 0
result = np.nanpercentile(data, 90, axis=0, method='linear')
print("nanpercentile 90 along axis 0:")
print(result)

# Verify manually for each cell
for i in range(2):
    for j in range(3):
        vals = data[:, i, j]
        valid = vals[~np.isnan(vals)]
        if len(valid) > 0:
            q = np.percentile(valid, 90, method='linear')
            if not np.isclose(q, result[i, j]):
                print(f"MISMATCH at ({i},{j}): manual={q}, auto={result[i,j]}, vals={valid}")

print("\nAll matched!")

# Test with a cell that has all NaN
data2 = np.array([
    [[np.nan, np.nan], [1.0, 2.0]],
    [[np.nan, np.nan], [3.0, 4.0]],
])
result2 = np.nanpercentile(data2, 90, axis=0, method='linear')
print("All-NaN cell result:", result2[0])
