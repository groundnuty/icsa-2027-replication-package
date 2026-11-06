
import numpy as np

# Test: verify hazen method
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
p90_hazen = np.percentile(x, 90, method='hazen')
print(f'numpy hazen p90 of [1,2,3,4,5]: {p90_hazen}')

# MATLAB type 5: position = (N+1)*p = 6*0.9 = 5.4 (1-indexed)
# Interpolate between 5th and 6th → x[5] = 5 (only 5 elements, so it's the last)
# Actually, position = 5.4, floor = 5, ceil = 6
# But we only have 5 elements. In MATLAB, it clamps?
# For N=5, position = 6*0.9 = 5.4, so it interpolates between 5th and 6th, but only 5 exist.
# MATLAB extrapolates using the formula.
# Actually, let me just check with a known example.

# Let me check against scipy
from scipy import stats
q = stats.mstats.mquantiles(x, prob=0.9, alphap=0.5, betap=0.5)  # This is type 5? No, let me check
print(f'scipy mquantiles with alphap=betap=0.5: {q}')

# Actually, let me just verify that hazen is consistent with the formula
# Formula: Q(p) = x[(N+1)*p - 1] (0-indexed, with linear interpolation)
# For N=5, p=0.9: position = 6*0.9 - 1 = 4.4
# Interpolate between x[4] and x[4+1] → but x[5] doesn't exist
# Wait, 4.4 = 4 + 0.4, so value = x[4] + 0.4*(x[5]-x[4]) but x[5] doesn't exist
# Actually, numpy handles this by clamping to the last value? Or extrapolating?

# Let me check with a larger array where it doesn't go out of bounds
y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
p90 = np.percentile(y, 90, method='hazen')
print(f'numpy hazen p90 of [1..10]: {p90}')

# Position (0-indexed): (10+1)*0.9 - 1 = 8.9
# Value = y[8] + 0.9*(y[9]-y[8]) = 9 + 0.9*1 = 9.9
print(f'Expected: 9.9')

# With MATLAB-style: 1-indexed position = (10+1)*0.9 = 9.9
# Value = y[9] + 0.9*(y[10]-y[9]) where y is 1-indexed
# y[9] = 9, y[10] = 10
# Value = 9 + 0.9*1 = 9.9 ✓

# Both give 9.9, confirming they're the same
