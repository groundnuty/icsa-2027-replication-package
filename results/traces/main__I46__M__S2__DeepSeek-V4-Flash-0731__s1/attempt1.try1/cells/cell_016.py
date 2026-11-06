
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')

def smooth_366(arr):
    """Smooth a 366-element array with a centered 31-day moving mean that wraps."""
    # arr: (366,) - per cell, per day-of-year
    n = 366
    window = 31
    half = 15
    result = np.full_like(arr, np.nan)
    for d in range(n):
        idxs = [(d + offset) % n for offset in range(-half, half + 1)]
        vals = arr[idxs]
        # Mean ignoring NaN? Or propagate NaN?
        # The method says unweighted centred 31-day moving mean.
        # Since sea cells have all valid values, this should be fine.
        # Let me use np.nanmean to handle potential NaN from day 60 interpolation in land cells.
        if not np.isnan(vals).all():
            result[d] = np.nanmean(vals)
        else:
            result[d] = np.nan
    return result

print("Smoothing threshold...")
threshold_smooth = np.zeros_like(threshold_raw)
for li in range(60):
    for loni in range(60):
        threshold_smooth[:, li, loni] = smooth_366(threshold_raw[:, li, loni])

print("Smoothing climatology...")
climatology_smooth = np.zeros_like(climatology_raw)
for li in range(60):
    for loni in range(60):
        climatology_smooth[:, li, loni] = smooth_366(climatology_raw[:, li, loni])

print("Done smoothing")
print("threshold_smooth shape:", threshold_smooth.shape)
print("NaN in threshold_smooth:", np.isnan(threshold_smooth).sum())
print("NaN in climatology_smooth:", np.isnan(climatology_smooth).sum())

# Save
np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/climatology_smooth.npy', climatology_smooth)
print("Saved smoothed results")
