
import numpy as np

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
tgt_doy = np.load('/tmp/tgt_doy.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Check that sea cells have valid thresholds for all target days
tgt_doy_min = tgt_doy.min()
tgt_doy_max = tgt_doy.max()
print("Target DOY range:", tgt_doy_min, "to", tgt_doy_max)

# Check threshold validity for sea cells across target days
sea_cells = np.where(sea_mask)
n_sea = len(sea_cells[0])
print("Sea cells:", n_sea)

# For each sea cell, check if threshold is finite for all target days
all_valid = True
for k in range(n_sea):
    i, j = sea_cells[0][k], sea_cells[1][k]
    for t in range(len(tgt_doy)):
        d = tgt_doy[t]
        if not np.isfinite(threshold_smooth[d, i, j]):
            all_valid = False
            print(f"Invalid threshold for sea cell ({i},{j}), day {t} (doy {d})")
            break
    if not all_valid:
        break

print("All sea cells have valid thresholds for all target days:", all_valid)

# Also check if there are non-sea cells with valid thresholds
# This is not critical but just checking
non_sea_mask = ~sea_mask
valid_thresh_count = np.sum(np.isfinite(threshold_smooth[tgt_doy_min:tgt_doy_max+1, :, :]), axis=(0,1)) > 0
print("Non-sea cells with at least some valid thresholds:", np.sum(valid_thresh_count & non_sea_mask))
