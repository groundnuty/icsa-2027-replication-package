
import numpy as np
import datetime as dt

# Verify: what does numpy 2.5's hazen actually compute?
# And compare with MATLAB's default quantile
x = np.arange(1, 122, dtype=np.float64)  # 1..121
print("numpy version:", np.__version__)
print(f"hazen p90: {np.percentile(x, 90, method='hazen')}")
print(f"linear p90: {np.percentile(x, 90, method='linear')}")

# The task says to use method='hazen'. In numpy 2.5, hazen gives
# h = N*p - 0.5 (0-based), which differs from MATLAB's h = (N-1)*p.
# I'll implement MATLAB's quantile manually to be safe.
# But first, let me check what the actual numpy hazen computes
# by examining if it's the same as MATLAB for our pool sizes.

# For our pools, N≈121 (or sometimes slightly fewer with NaN removed).
# Let me verify with actual pool data.

# Check: does np.percentile with method='hazen' match manual MATLAB for a sample?
np.random.seed(42)
data = np.random.randn(121) * 2 + 290
q_hazen = np.percentile(data, 90, method='hazen')
q_linear = np.percentile(data, 90, method='linear')

# Manual MATLAB
sorted_data = np.sort(data)
n = len(sorted_data)
h = (n-1)*0.9 + 1
idx_floor = int(np.floor(h)) - 1
idx_ceil = int(np.ceil(h)) - 1
g = h - np.floor(h)
q_matlab = (1-g)*sorted_data[idx_floor] + g*sorted_data[idx_ceil]

print(f"\nFor N=121 pool:")
print(f"  hazen: {q_hazen:.6f}")
print(f"  linear: {q_linear:.6f}")
print(f"  MATLAB manual: {q_matlab:.6f}")
print(f"  hazen == MATLAB? {abs(q_hazen - q_matlab) < 1e-10}")
print(f"  linear == MATLAB? {abs(q_linear - q_matlab) < 1e-10}")
