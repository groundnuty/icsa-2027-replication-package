
import numpy as np

# Verify np.percentile with method='hazen' is available and correct
print("numpy version:", np.__version__)
print("hazen method available:", 'hazen' in np.percentile.__doc__)

# Test with a small example
x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)
p90 = np.percentile(x, 90, method='hazen')
print(f"90th percentile of 1-10 (hazen): {p90}")
print(f"Expected: 9.1 (position (10-1)*0.9+1 = 9.1, so value at position 9.1)")
print(f"  x[8]=9, x[9]=10, interpolated: 9 + 0.1*(10-9) = 9.1")

# Test nanpercentile with method
x2 = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
p90_2 = np.nanpercentile(x2, 90, method='hazen')
print(f"\nnanpercentile 90 (hazen): {p90_2}")

# Test with a simple 2D case
arr2d = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0]])
p90_2d = np.nanpercentile(arr2d, 90, axis=0, method='hazen')
print(f"\n2D percentile along axis 0: {p90_2d}")
print(f"Expected: col 0: 8.2, col 1: 9.2")
