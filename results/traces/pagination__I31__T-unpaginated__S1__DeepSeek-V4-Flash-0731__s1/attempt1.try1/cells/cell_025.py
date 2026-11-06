
import numpy as np

x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)

# Test different percentiles with hazen
for p in [0, 0.25, 0.5, 0.75, 0.9, 1.0]:
    val = np.percentile(x, p*100, method='hazen')
    h = (len(x)-1)*p + 1
    print(f"p={p}: hazen={val}, h={h:.2f}")

print()

# Test with method='linear' (default)
for p in [0, 0.25, 0.5, 0.75, 0.9, 1.0]:
    val = np.percentile(x, p*100, method='linear')
    print(f"p={p}: linear={val}")

# Check what MATLAB would give
# MATLAB quantile(x, 0.9) = ?
# Using the formula from MATLAB docs:
# position = (n-1)*p + 1 = 9.1
# Interpolate between x(9) and x(10) = 9 and 10
# = 9 + 0.1*(10-9) = 9.1
print("\nExpected MATLAB result for p=0.9: 9.1")
print("numpy hazen result:", np.percentile(x, 90, method='hazen'))
