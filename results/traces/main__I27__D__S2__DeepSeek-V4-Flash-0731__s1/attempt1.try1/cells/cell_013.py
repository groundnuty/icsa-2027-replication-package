
import numpy as np

thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')

nlat, nlon = thresholds.shape[1], thresholds.shape[2]

def smooth_wrap(arr, window=31):
    """Smooth a 366-element array with an unweighted centred moving mean that wraps around.
    arr: (366, nlat, nlon)
    Returns: (366, nlat, nlon)
    """
    half = window // 2  # 15
    n = arr.shape[0]  # 366
    result = np.zeros_like(arr)
    
    # For each day d (0-indexed), average days d-15 to d+15 (mod 366)
    # We need to handle NaN: if any value in the window is NaN, the result is NaN
    # But for sea cells, all values are valid, so no issue.
    # For land cells, all values are NaN, so result is NaN.
    
    # Use a circular approach: concatenate the array 3 times and use a rolling sum
    # But NaN handling is tricky. Let's just use a loop over days.
    
    # Build indices for each day's window
    # For day d, the window is [(d-15) mod 366, ..., (d+15) mod 366]
    all_indices = np.arange(n)
    for d in range(n):
        window_indices = [(d - 15 + k) % n for k in range(window)]
        # If any value is NaN in the window for a given cell, the mean is NaN
        # Use np.nanmean only if there are valid values; otherwise NaN
        for i in range(nlat):
            for j in range(nlon):
                vals = arr[window_indices, i, j]
                if np.all(np.isnan(vals)):
                    result[d, i, j] = np.nan
                else:
                    result[d, i, j] = np.nanmean(vals)
    return result

# This might be slow. Let me vectorize.
# Actually, since sea cells have all valid values and land cells all NaN,
# I can use a simpler approach with rolling sum.

def smooth_wrap_fast(arr, window=31):
    """Vectorized smoothing with wrapping."""
    half = window // 2
    n = arr.shape[0]
    # Extend the array circularly
    # We need n+window-1 values, from index -half to index half+n-1
    ext = np.concatenate([arr[-half:], arr, arr[:half+1]], axis=0)  # shape (n+2*half, nlat, nlon)
    # Wait, that's not right for the wrapping
    # For day d (0-indexed), window is [(d-15) mod n, ..., (d+15) mod n]
    # These are n consecutive indices in the extended array starting at position d
    # (since we have arr[-15:] followed by arr followed by arr[:16])
    # ext[k] for k=0..14 corresponds to arr[-15+k], ext[k] for k=15..380 corresponds to arr[k-15]
    # ext[k] for k=381..396 corresponds to arr[k-381] (i.e., arr[0..15])
    
    # Actually, let me just use a simple approach:
    # For each cell, use numpy convolve on the circular data
    
    # First, extend the array
    ext_arr = np.concatenate([arr, arr, arr], axis=0)  # 3*n copies
    
    # For day d (0-indexed), the window in the extended array is positions d+n to d+n+30 (31 values)
    # Wait, let me think again.
    # In the extended array (3*n), day d is at positions d, d+n, d+2n.
    # The window of day d is [d-15, d+15] mod n.
    # In the extended array, that's [d+n-15, d+n+15], which is 31 consecutive values.
    
    result = np.zeros_like(arr)
    for i in range(nlat):
        for j in range(nlon):
            col = ext_arr[:, i, j]  # (3*n,)
            # For each day d, compute mean of col[d+n-15 : d+n+16]
            for d in range(n):
                window_vals = col[d+n-15 : d+n+16]
                if np.all(np.isnan(window_vals)):
                    result[d, i, j] = np.nan
                else:
                    result[d, i, j] = np.nanmean(window_vals)
    
    return result

# Even faster: use convolution
def smooth_wrap_conv(arr, window=31):
    """Vectorized smoothing using convolution."""
    n = arr.shape[0]
    half = window // 2
    # Extend: arr[-15:], arr, arr[:16]
    ext = np.concatenate([arr[-half:], arr, arr[:half+1]], axis=0)  # (n+2*half, nlat, nlon)
    
    # Use a moving sum via cumsum along axis 0
    # For each output position d (0 to n-1), sum ext[d : d+window]
    # cumsum of ext
    cs = np.concatenate([np.zeros((1, arr.shape[1], arr.shape[2])), np.cumsum(np.nan_to_num(ext, nan=0.0), axis=0)], axis=0)
    # Sum of ext[d:d+window] = cs[d+window] - cs[d]
    sums = cs[half+1:half+1+n+1] - cs[half:half+n+1]  # Wait, let me reconsider.
    
    # Actually, ext has n+2*half = n+30 elements, indexed 0 to n+29
    # For day d (0-indexed), window is ext[d : d+31]
    # cs[k] = sum of ext[0:k], so sum of ext[d:d+31] = cs[d+31] - cs[d]
    # For d from 0 to n-1, d+31 goes from 31 to n+30 = n+30
    # cs has n+31 elements (0 to n+30)
    
    cs = np.concatenate([np.zeros((1, arr.shape[1], arr.shape[2])), 
                          np.cumsum(np.nan_to_num(ext, nan=0.0), axis=0)], axis=0)
    sums = cs[window:] - cs[:n]  # shape (n, nlat, nlon)
    
    # For NaN, we need to count valid values in each window
    valid = ~np.isnan(ext)
    cs_valid = np.concatenate([np.zeros((1, arr.shape[1], arr.shape[2])), 
                                np.cumsum(valid.astype(np.float64), axis=0)], axis=0)
    counts = cs_valid[window:] - cs_valid[:n]  # shape (n, nlat, nlon)
    
    result = np.where(counts > 0, sums / counts, np.nan)
    return result

# Test
thr_smooth = smooth_wrap_conv(thresholds)
cli_smooth = smooth_wrap_conv(climatology)

# Check
print("NaN count in smoothed thresholds:", np.isnan(thr_smooth).sum())
print("NaN count in smoothed climatology:", np.isnan(cli_smooth).sum())

# Verify some values against a simple loop
# Day 0 (Jan 1), sea cell
d = 0  # day of year 1
i, j = 0, 0
window_indices = [(d - 15 + k) % 366 for k in range(31)]
vals = thresholds[window_indices, i, j]
manual_mean = np.mean(vals)
print(f"Manual mean day 1 cell (0,0): {manual_mean}")
print(f"Conv mean day 1 cell (0,0): {thr_smooth[0, i, j]}")

np.save('/work/thr_smooth.npy', thr_smooth)
np.save('/work/cli_smooth.npy', cli_smooth)
print("Saved")
