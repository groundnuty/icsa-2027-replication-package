
import numpy as np

thresholds = np.load('/tmp/thresholds.npy')
climatology = np.load('/tmp/climatology.npy')

n_lat, n_lon = thresholds.shape[1], thresholds.shape[2]

def smooth_wrap(arr):
    """Smooth a 366-element array with unweighted centred 31-day moving mean that wraps."""
    # arr shape: (366,)
    # For day d (0-indexed), average arr[(d-15) % 366] to arr[(d+15) % 366]
    result = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + offset) % 366 for offset in range(-15, 16)]
        result[d] = np.nanmean(arr[indices])
    return result

# Apply smoothing to each cell
thr_smooth = np.zeros_like(thresholds)
cli_smooth = np.zeros_like(climatology)

for i in range(n_lat):
    for j in range(n_lon):
        thr_smooth[:, i, j] = smooth_wrap(thresholds[:, i, j])
        cli_smooth[:, i, j] = smooth_wrap(climatology[:, i, j])

print(f"Smoothed thresholds NaN count: {np.isnan(thr_smooth).sum()}")
print(f"Smoothed climatology NaN count: {np.isnan(cli_smooth).sum()}")

np.save('/tmp/thr_smooth.npy', thr_smooth)
np.save('/tmp/cli_smooth.npy', cli_smooth)
print("Saved smoothed arrays")
