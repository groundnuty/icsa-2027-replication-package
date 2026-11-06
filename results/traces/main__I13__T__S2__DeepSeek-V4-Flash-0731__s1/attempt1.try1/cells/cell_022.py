
import numpy as np

sst_base = np.load('sst_base.npy')
sst_target = np.load('sst_target.npy')
thresholds = np.load('thresholds_raw.npy')

# For each cell, check NaN pattern in baseline
nan_per_cell = np.sum(np.isnan(sst_base), axis=0)  # (60, 60)
print("NaN count in baseline per cell (unique values):", np.unique(nan_per_cell))
print("Cells with 0 NaN:", (nan_per_cell == 0).sum())
print("Cells with >0 NaN:", (nan_per_cell > 0).sum())

# Check if all cells with >0 NaN in baseline are the same as all-NaN in target
all_nan_target = np.all(np.isnan(sst_target), axis=0)
print("Cells with >0 NaN in baseline == all NaN in target:",
      np.array_equal((nan_per_cell > 0), all_nan_target))

# Check target NaN pattern
nan_per_cell_target = np.sum(np.isnan(sst_target), axis=0)
print("NaN count in target per cell (unique values):", np.unique(nan_per_cell_target))
