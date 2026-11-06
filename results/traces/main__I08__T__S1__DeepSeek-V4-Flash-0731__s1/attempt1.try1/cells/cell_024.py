
import numpy as np

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
target_data = np.load('/tmp/target_data.npy')
tgt_doy = np.load('/tmp/tgt_doy.npy')
tgt_times = np.load('/tmp/tgt_times.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

n_time, n_lat, n_lon = target_data.shape

# Convert to float64
target_data_f64 = target_data.astype(np.float64)

# For each sea cell, determine hot days
# hot[t, i, j] = 1 if SST >= threshold for that day's doy
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    d = tgt_doy[t]
    # Get threshold for this day-of-year for all cells
    thresh = threshold_smooth[d, :, :]
    # Only consider sea cells
    valid = np.isfinite(target_data_f64[t]) & sea_mask
    hot[t] = valid & (target_data_f64[t] >= thresh)

print("Hot days count:", hot.sum())
print("Sea cells:", sea_mask.sum())

# Now find per-cell MHWs
# For each cell: find runs of >=5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

# mhw_mask[t, i, j] = 1 if cell is inside a per-cell MHW on day t
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

sea_indices = np.where(sea_mask)
n_sea = len(sea_indices[0])
print(f"Processing {n_sea} sea cells...")

import datetime as dt

for k in range(n_sea):
    i, j = sea_indices[0][k], sea_indices[1][k]
    
    # Get hot days for this cell
    hot_cell = hot[:, i, j]  # (n_time,)
    
    # Find runs of hot days
    # First, identify all maximal runs of consecutive hot days
    runs = []  # list of (start, end) inclusive
    in_run = False
    for t in range(n_time):
        if hot_cell[t]:
            if not in_run:
                run_start = t
                in_run = True
        else:
            if in_run:
                runs.append((run_start, t-1))
                in_run = False
    if in_run:
        runs.append((run_start, n_time-1))
    
    # Keep only runs of >= 5 days
    long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    
    if len(long_runs) == 0:
        continue
    
    # Join runs separated by 1-2 non-hot days
    joined_runs = []
    current = long_runs[0]
    for r in long_runs[1:]:
        gap = r[0] - current[1] - 1
        if gap <= 2:
            # Join
            current = (current[0], r[1])
        else:
            joined_runs.append(current)
            current = r
    joined_runs.append(current)
    
    # Mark the joined runs in the mask
    for (start, end) in joined_runs:
        mhw_mask[start:end+1, i, j] = 1
    
    if k % 1000 == 0:
        print(f"  Processed {k} cells...")

print(f"Done. Total MHW cell-days: {mhw_mask.sum()}")

# Save intermediate
np.save('/tmp/mhw_mask.npy', mhw_mask)
np.save('/tmp/hot.npy', hot)
print("Saved MHW mask and hot array.")
