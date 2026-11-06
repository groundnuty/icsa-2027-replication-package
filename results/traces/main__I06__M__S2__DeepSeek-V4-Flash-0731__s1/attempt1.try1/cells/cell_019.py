
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
clim_raw = np.load('/tmp/clim_raw.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Check NaN in raw threshold/clim
print("NaN in threshold_raw:", np.isnan(threshold_raw[1:367]).sum(), "out of", threshold_raw[1:367].size)
print("NaN in clim_raw:", np.isnan(clim_raw[1:367]).sum(), "out of", clim_raw[1:367].size)

# Check which cells have any NaN in threshold
nan_mask_thr = np.isnan(threshold_raw[1:367]).any(axis=0)  # (60, 60)
print("Cells with any NaN threshold:", nan_mask_thr.sum())
print("Sea cells that are NaN threshold:", (nan_mask_thr & sea_cells).sum())

# Check specific sea cell values
print("\nThreshold for day 153, sea cells:")
# Find a sea cell
sea_idx = np.where(sea_cells)
print("First sea cell:", sea_idx[0][0], sea_idx[1][0])
i, j = sea_idx[0][0], sea_idx[1][0]
print(f"  Cell ({i},{j}): day 59={threshold_raw[59,i,j]}, day 60={threshold_raw[60,i,j]}, day 61={threshold_raw[61,i,j]}")
print(f"  Clim: day 59={clim_raw[59,i,j]}, day 60={clim_raw[60,i,j]}, day 61={clim_raw[61,i,j]}")
