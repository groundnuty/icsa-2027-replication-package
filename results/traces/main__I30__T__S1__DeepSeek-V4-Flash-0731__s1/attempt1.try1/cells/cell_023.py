
import numpy as np

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Count NaN in threshold for sea cells
n_doy, n_lat, n_lon = threshold_smooth.shape
nan_count = 0
for i in range(n_lat):
    for j in range(n_lon):
        if sea_mask[i, j]:
            for d in range(n_doy):
                if np.isnan(threshold_smooth[d, i, j]):
                    nan_count += 1
print("NaN count in smoothed threshold for sea cells:", nan_count)

# Also check unsmoothed (recompute is expensive, let me just check which days are NaN)
# Let me check a specific cell
i, j = 0, 0
# Find a sea cell
for ii in range(n_lat):
    for jj in range(n_lon):
        if sea_mask[ii, jj]:
            i, j = ii, jj
            break
    if sea_mask[i, j]:
        break

print(f"Checking cell ({i}, {j})")
thr_cell = threshold_smooth[:, i, j]
nan_days = np.where(np.isnan(thr_cell))[0]
print(f"NaN days in threshold for this cell: {nan_days}")
print(f"Number of NaN days: {len(nan_days)}")
