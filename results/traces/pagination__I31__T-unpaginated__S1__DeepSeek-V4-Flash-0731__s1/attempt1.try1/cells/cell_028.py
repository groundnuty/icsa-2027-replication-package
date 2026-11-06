
import numpy as np
import datetime as dt

# First, let me verify the percentile computation.
# MATLAB's default quantile uses h = (n-1)*p + 1 (1-based) with linear interpolation.
# numpy's 'linear' method matches this. numpy's 'hazen' in v2.5 does NOT match.
# Let me verify with a known case.

x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
# MATLAB: h = 9*0.9+1 = 9.1 (1-based) -> x(9) + 0.1*(x(10)-x(9)) = 9 + 0.1*1 = 9.1
print(f"linear p90: {np.percentile(x, 90, method='linear')}")  # should be 9.1
print(f"hazen p90: {np.percentile(x, 90, method='hazen')}")    # gives 9.5 in numpy 2.5

# Let me implement MATLAB's quantile manually
def matlab_quantile(data, p):
    """MATLAB default quantile: h = (n-1)*p + 1, linear interpolation."""
    data = np.asarray(data, dtype=np.float64)
    valid = data[~np.isnan(data)]
    if len(valid) == 0:
        return np.nan
    sorted_vals = np.sort(valid)
    n = len(sorted_vals)
    h = (n - 1) * p + 1  # 1-based
    if h <= 1:
        return sorted_vals[0]
    if h >= n:
        return sorted_vals[-1]
    idx_floor = int(np.floor(h)) - 1  # 0-based
    idx_ceil = int(np.ceil(h)) - 1
    g = h - np.floor(h)
    return (1 - g) * sorted_vals[idx_floor] + g * sorted_vals[idx_ceil]

# Test
print(f"Manual MATLAB quantile: {matlab_quantile(x, 0.9)}")  # should be 9.1

# Also verify numpy linear matches
print(f"numpy linear: {np.percentile(x, 90, method='linear')}")

# Test with NaN
x_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
print(f"Manual MATLAB quantile (with NaN): {matlab_quantile(x_nan, 0.9)}")
print(f"numpy nanpercentile linear: {np.nanpercentile(x_nan, 90, method='linear')}")
