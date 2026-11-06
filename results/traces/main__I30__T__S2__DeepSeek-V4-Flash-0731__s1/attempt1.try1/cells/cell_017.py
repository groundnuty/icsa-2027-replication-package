
import numpy as np

threshold = np.load('/tmp/threshold.npy')
climatology = np.load('/tmp/climatology.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

print("threshold shape:", threshold.shape)
print("climatology shape:", climatology.shape)
print("Sea cells:", sea_mask.sum())

# Apply 31-day moving average (wrapping around year)
def smooth_wrap(arr):
    """Smooth a 366-element array with unweighted centred 31-day moving mean that wraps."""
    n = len(arr)  # should be 366
    result = np.full_like(arr, np.nan)
    for d in range(n):
        # Average days d-15 to d+15 (mod 366)
        indices = [(d + offset) % n for offset in range(-15, 16)]
        values = arr[indices]
        valid = values[~np.isnan(values)]
        if len(valid) > 0:
            result[d] = np.mean(valid)
    return result

# Apply smoothing for each sea cell
threshold_smooth = np.full_like(threshold, np.nan)
climatology_smooth = np.full_like(climatology, np.nan)

for lat_i in range(60):
    for lon_j in range(60):
        if sea_mask[lat_i, lon_j]:
            threshold_smooth[:, lat_i, lon_j] = smooth_wrap(threshold[:, lat_i, lon_j])
            climatology_smooth[:, lat_i, lon_j] = smooth_wrap(climatology[:, lat_i, lon_j])

print("Smoothing complete")
print("threshold_smooth shape:", threshold_smooth.shape)
print("Any NaN in threshold_smooth for sea cells:", np.isnan(threshold_smooth[:, sea_mask]).any())
print("Any NaN in climatology_smooth for sea cells:", np.isnan(climatology_smooth[:, sea_mask]).any())

# Save
np.save('/tmp/threshold_smooth.npy', threshold_smooth)
np.save('/tmp/climatology_smooth.npy', climatology_smooth)
