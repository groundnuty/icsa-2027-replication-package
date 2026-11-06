
import numpy as np

thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')

n = 366
half = 15
window = 31

def smooth_wrap_conv(arr, window=31, half=15):
    """Vectorized smoothing with wrapping using convolution/cumsum."""
    n = arr.shape[0]
    # Extended array: for day d (0..n-1), window is ext[d : d+window]
    # We need ext to have at least n+window-1 = n+2*half elements
    # Build: arr[-half:] + arr + arr[:half]
    ext = np.concatenate([arr[-half:], arr, arr[:half]], axis=0)  # (n+2*half, nlat, nlon)
    
    # Cumulative sum with NaN handling
    data_for_cs = np.nan_to_num(ext, nan=0.0)
    valid = ~np.isnan(ext)
    
    cs = np.concatenate([np.zeros((1, arr.shape[1], arr.shape[2])), 
                          np.cumsum(data_for_cs, axis=0)], axis=0)
    cs_valid = np.concatenate([np.zeros((1, arr.shape[1], arr.shape[2])), 
                                np.cumsum(valid.astype(np.float64), axis=0)], axis=0)
    
    # For day d: sum = cs[d+window] - cs[d]
    sums = cs[window:] - cs[:n]  # cs[31:] - cs[:366]
    counts = cs_valid[window:] - cs_valid[:n]
    
    result = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
    return result

thr_smooth = smooth_wrap_conv(thresholds)
cli_smooth = smooth_wrap_conv(climatology)

print("thr_smooth shape:", thr_smooth.shape)
print("NaN count in smoothed thresholds:", np.isnan(thr_smooth).sum())
print("NaN count in smoothed climatology:", np.isnan(cli_smooth).sum())

# Verify against manual calculation
d = 0  # day of year 1
i, j = 0, 0
window_indices = [(d - 15 + k) % 366 for k in range(31)]
vals = thresholds[window_indices, i, j]
manual_mean = np.mean(vals)
print(f"Manual mean day 1 cell (0,0): {manual_mean}")
print(f"Conv mean day 1 cell (0,0): {thr_smooth[0, i, j]}")

# Verify wrapping
# Day 366 (index 365): window should include days 351-366, 1-15
d = 365
window_indices = [(d - 15 + k) % 366 for k in range(31)]
vals = thresholds[window_indices, i, j]
manual_mean = np.mean(vals)
print(f"Manual mean day 366 cell (0,0): {manual_mean}")
print(f"Conv mean day 366 cell (0,0): {thr_smooth[365, i, j]}")

np.save('/work/thr_smooth.npy', thr_smooth)
np.save('/work/cli_smooth.npy', cli_smooth)
print("Saved")
