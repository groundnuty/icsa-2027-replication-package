
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
clim_raw = np.load('/tmp/clim_raw.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Check for each sea cell if any non-60 doy has NaN
sea_threshold = threshold_raw[1:367, :, :]  # (366, 60, 60)
# Exclude doy 60 (which is at index 59 in the 0-based array)
doy60_idx = 59  # 0-based index for doy 60
mask = np.arange(366) != doy60_idx
sea_nan_non60 = np.isnan(sea_threshold[mask]).any(axis=0)
print("Sea cells with NaN threshold for non-60 doy:", (sea_nan_non60 & sea_cells).sum())

# Check specific sea cells
if (sea_nan_non60 & sea_cells).sum() > 0:
    bad_cells = np.where(sea_nan_non60 & sea_cells)
    for k in range(min(5, len(bad_cells[0]))):
        i, j = bad_cells[0][k], bad_cells[1][k]
        bad_doy = np.where(np.isnan(threshold_raw[1:367, i, j]))[0] + 1
        bad_doy = bad_doy[bad_doy != 60]
        print(f"  Cell ({i},{j}): NaN doy values: {bad_doy}")
else:
    print("No sea cells have NaN for non-60 doy in threshold")

# Now check after filling day 60
threshold_filled = threshold_raw.copy()
clim_filled = clim_raw.copy()
threshold_filled[60] = (threshold_filled[59] + threshold_filled[61]) / 2
clim_filled[60] = (clim_filled[59] + clim_filled[61]) / 2

# Check sea cells with NaN after filling
sea_nan_all = np.isnan(threshold_filled[1:367]).any(axis=0)
print("Sea cells with any NaN after day 60 fill:", (sea_nan_all & sea_cells).sum())
