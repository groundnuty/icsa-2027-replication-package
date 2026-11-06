
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Check if any sea cell has NaN raw threshold for any day-of-year
sea_indices = np.where(sea_mask)
n_sea = len(sea_indices[0])

nan_raw_count = 0
nan_smooth_count = 0
for k in range(n_sea):
    i, j = sea_indices[0][k], sea_indices[1][k]
    if np.any(~np.isfinite(threshold_raw[1:, i, j])):
        nan_raw_count += 1
        if nan_raw_count <= 3:
            bad_days = np.where(~np.isfinite(threshold_raw[1:, i, j]))[0] + 1
            print(f"Sea cell ({i},{j}) has NaN raw threshold for days: {bad_days}")
    if np.any(~np.isfinite(threshold_smooth[1:, i, j])):
        nan_smooth_count += 1
        if nan_smooth_count <= 3:
            bad_days = np.where(~np.isfinite(threshold_smooth[1:, i, j]))[0] + 1
            print(f"Sea cell ({i},{j}) has NaN smooth threshold for days: {bad_days}")

print(f"\nSea cells with NaN raw threshold (any day): {nan_raw_count}/{n_sea}")
print(f"Sea cells with NaN smooth threshold (any day): {nan_smooth_count}/{n_sea}")
