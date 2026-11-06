
import numpy as np

# Load intermediate results
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_time_idx = np.load('/tmp/target_time_idx.npy')

print("Threshold shape:", threshold_smooth.shape)
print("Climatology shape:", climatology_smooth.shape)
print("Sea cells shape:", sea_cells.shape, "sum:", sea_cells.sum())
print("Target SST shape:", target_sst.shape)
print("Target time idx:", target_time_idx[0], target_time_idx[-1], "count:", len(target_time_idx))

# Check that threshold and climatology have no NaN for sea cells
sea_thresh = threshold_smooth[:, sea_cells]
sea_clim = climatology_smooth[:, sea_cells]
print("NaN in sea threshold:", np.isnan(sea_thresh).sum())
print("NaN in sea climatology:", np.isnan(sea_clim).sum())
