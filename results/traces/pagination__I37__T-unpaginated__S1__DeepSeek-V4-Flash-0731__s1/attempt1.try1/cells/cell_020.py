
import numpy as np

threshold = np.load('work/threshold.npy')
climatology = np.load('work/climatology.npy')

print(f"Threshold shape: {threshold.shape}")

# Smoothing: 31-day moving mean, wrapping around 366 days
# For each day d (0-indexed), average days d-15 to d+15 (mod 366)
# Use convolution with circular padding

def smooth_wrap(arr, window=31):
    """Smooth a 366 x n_cells array with a centred moving mean that wraps."""
    n = arr.shape[0]
    half = window // 2  # 15
    # Pad circularly
    padded = np.vstack([arr[-half:], arr, arr[:half]])
    # Compute cumulative sum for rolling mean
    cumsum = np.cumsum(padded, axis=0)
    result = np.zeros_like(arr)
    for d in range(n):
        start = d
        end = d + window
        if start == 0:
            result[d] = cumsum[end - 1] / window
        else:
            result[d] = (cumsum[end - 1] - cumsum[start - 1]) / window
    return result

# Alternative: use np.convolve for each cell
def smooth_wrap2(arr, window=31):
    """Smooth a 366 x n_cells array with a centred moving mean that wraps."""
    n = arr.shape[0]
    half = window // 2
    result = np.zeros_like(arr)
    for c in range(arr.shape[1]):
        col = arr[:, c]
        for d in range(n):
            idx = [(d + i) % n for i in range(-half, half + 1)]
            vals = col[idx]
            result[d, c] = np.mean(vals)
    return result

# Actually let me use a vectorized approach
def smooth_wrap3(arr, window=31):
    """Smooth a 366 x n_cells array with a centred moving mean that wraps."""
    n = arr.shape[0]
    half = window // 2
    # Create index matrix
    idx = np.array([(np.arange(n) + i) % n for i in range(-half, half+1)])
    # idx shape: (31, 366)
    # For each day d, take column d
    result = np.zeros_like(arr)
    for d in range(n):
        result[d] = np.mean(arr[idx[:, d], :], axis=0)
    return result

# Test on small example
test = np.arange(366*3).reshape(366, 3).astype(float)
r1 = smooth_wrap(test)
r2 = smooth_wrap3(test)
print(f"Test match: {np.allclose(r1, r2)}")

# Let me verify with a specific example
# For day 0, average days -15, -14, ..., 0, ..., 15 (mod 366)
# That's days 351, 352, ..., 365, 0, 1, ..., 15
# For the test array, arr[d, c] = d * 3 + c
# Mean of arr[351:366, c] and arr[0:16, c] = mean of indices 351-365 and 0-15
# That's 31 values: 351-365 (15 values) and 0-15 (16 values)
# Sum = sum(351..365) * 3 + 16*3 + sum(0..15)*3 + ... hmm let me just check

# Verify day 0 for cell 0
# Values: arr[351,0]=1053, arr[352,0]=1056, ..., arr[365,0]=1095, arr[0,0]=0, ..., arr[15,0]=45
# Sum of 351..365 = 15*(351+365)/2 = 15*358 = 5370. Times 3 = 16110
# Plus sum of 0..15 = 16*15/2 = 120. Times 3 = 360
# Total = 16470, / 31 = 531.29...
expected = (sum(range(351, 366)) + sum(range(0, 16))) * 3 / 31
print(f"Day 0, cell 0: smooth={r1[0,0]}, expected={expected}")

# Now apply to actual data
threshold_smooth = smooth_wrap3(threshold)
climatology_smooth = smooth_wrap3(climatology)

print(f"Threshold_smooth shape: {threshold_smooth.shape}")
print(f"Threshold_smooth NaN count: {np.isnan(threshold_smooth).sum()}")
print(f"Climatology_smooth NaN count: {np.isnan(climatology_smooth).sum()}")

# Check: for cells with no NaN, smoothed values should be all valid
nan_count_smooth = np.sum(np.isnan(threshold_smooth), axis=0)
print(f"Cells with all NaN in smoothed threshold: {(nan_count_smooth == 366).sum()}")
print(f"Cells with no NaN in smoothed threshold: {(nan_count_smooth == 0).sum()}")
print(f"Cells with partial NaN in smoothed threshold: {((nan_count_smooth > 0) & (nan_count_smooth < 366)).sum()}")

np.save('work/threshold_smooth.npy', threshold_smooth)
np.save('work/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed threshold and climatology")
