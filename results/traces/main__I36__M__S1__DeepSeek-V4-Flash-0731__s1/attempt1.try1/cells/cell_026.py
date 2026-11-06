
import numpy as np

threshold_smoothed = np.load('/tmp/threshold_smoothed.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Check if any sea cells have NaN thresholds for any doy in target period
# Target period doys: 153-244 (June 1 - Aug 31)
n_sea = sea_cells.sum()
print(f"Sea cells: {n_sea}")

# For each target day doy, check if any sea cell has NaN threshold
for doy in range(153, 245):
    idx = doy - 1
    nan_mask = np.isnan(threshold_smoothed[idx]) & sea_cells
    if nan_mask.sum() > 0:
        print(f"doy {doy}: {nan_mask.sum()} sea cells with NaN threshold")
        break
else:
    print("No sea cells have NaN threshold for any target day")

# Also check climatology
climatology_smoothed = np.load('/tmp/climatology_smoothed.npy')
for doy in range(153, 245):
    idx = doy - 1
    nan_mask = np.isnan(climatology_smoothed[idx]) & sea_cells
    if nan_mask.sum() > 0:
        print(f"Climatology doy {doy}: {nan_mask.sum()} sea cells with NaN")
        break
else:
    print("No sea cells have NaN climatology for any target day")
