
import numpy as np

# Test: what does numpy method='hazen' actually compute?
# Let me compare with the Hyndman-Fan type 5 formula
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

# Type 5 (Hazen): h = N*p + 1/2
p = 0.9
N = len(x)
h = N * p + 0.5
print(f"N={N}, p={p}, h={h}")
# h = 9.5, so Q = x_9 + 0.5*(x_10 - x_9) = 9 + 0.5*1 = 9.5
print(f"Manual type 5: {x[8] + (h - 8) * (x[9] - x[8])}")

# numpy hazen
print(f"numpy hazen: {np.percentile(x, 90, method='hazen')}")

# Also test with nans
x_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
# Remove NaN, we have 9 values: [1,2,4,5,6,7,8,9,10]
print(f"After removing NaN: {x_nan[~np.isnan(x_nan)]}")
# N=9, h = 9*0.9 + 0.5 = 8.6
# Q = x_8 + 0.6*(x_9 - x_8)... but there are only 9 values (indices 0-8)
# So Q = x[8] = 10.0
x_clean = x_nan[~np.isnan(x_nan)]
print(f"Manual: {x_clean[7] + 0.6*(x_clean[8] - x_clean[7])}")  # h=8.6, floor=8, so x_9th + 0.6*(x_10th - x_9th)
# Actually index 7 = 9, index 8 = 10
# Q = 9 + 0.6*(10-9) = 9.6

# Hmm, let me recompute
# N=9, p=0.9, h = 9*0.9 + 0.5 = 8.6
# Since 1 ≤ h ≤ N, Q(p) = x_⌊h⌋ + (h-⌊h⌋)*(x_⌊h⌋+1 - x_⌊h⌋)
# ⌊8.6⌋ = 8, so Q = x_8 + 0.6*(x_9 - x_8)
# But x has indices 0-8 (9 values), so x_8 is the 9th value = 10
# There is no x_9, so the formula would break.
# Actually, h=8.6, and if h > N-1 (which is 8), then... hmm.

# Actually, the Hyndman-Fan type 5 formula assumes 1-indexed positions:
# Q(p) = x_{(⌊h⌋)} + (h - ⌊h⌋) * (x_{(⌊h⌋+1)} - x_{(⌊h⌋)})
# where x_{(i)} is the i-th order statistic (1-indexed).
# If h = 8.6, then ⌊h⌋ = 8, so Q = x_{(8)} + 0.6*(x_{(9)} - x_{(8)})
# x_{(8)} is the 8th smallest = 9 (0-indexed: x_clean[7])
# x_{(9)} is the 9th smallest = 10 (0-indexed: x_clean[8])
# Q = 9 + 0.6*(10-9) = 9.6

print(f"Manual type 5 with 1-indexing: 9 + 0.6*(10-9) = {9 + 0.6*(10-9)}")

# numpy with nan
print(f"numpy nanpercentile hazen: {np.nanpercentile(x_nan, 90, method='hazen')}")

# Actually wait, does np.nanpercentile support method='hazen'?
print(f"numpy nanpercentile hazen: {np.nanpercentile(x_nan, 90, method='hazen')}")
