
import numpy as np

# Test percentile on float32
x = np.array([1.5, 2.5, 3.5, 4.5, 5.5], dtype=np.float32)
p = np.percentile(x, 90, method='hazen')
print(f"Percentile dtype: {p.dtype}")
m = np.mean(x)
print(f"Mean dtype: {m.dtype}")

# Test with NaN
x_nan = np.array([1.5, 2.5, np.nan, 4.5, 5.5], dtype=np.float32)
valid = x_nan[~np.isnan(x_nan)]
p2 = np.percentile(valid, 90, method='hazen')
print(f"Percentile (no NaN) dtype: {p2.dtype}")

# Check nanpercentile with method
try:
    p3 = np.nanpercentile(x_nan, 90, method='hazen')
    print(f"nanpercentile with method: {p3}, dtype: {p3.dtype}")
except Exception as e:
    print(f"nanpercentile with method failed: {e}")

# Compare float32 vs float64 computation
x32 = np.random.rand(100).astype(np.float32) * 100
x64 = x32.astype(np.float64)
p32 = np.percentile(x32, 90, method='hazen')
p64 = np.percentile(x64, 90, method='hazen')
print(f"\nPercentile float32 input: {p32}")
print(f"Percentile float64 input: {p64}")
print(f"Difference: {abs(p32 - p64)}")
