
import numpy as np

thresholds = np.load('thresholds_raw.npy')

# Check which cells have all-NaN thresholds (land cells)
all_nan_cells = np.all(np.isnan(thresholds), axis=0)  # shape (60, 60)
print("Cells with all-NaN thresholds:", all_nan_cells.sum())
print("Total cells:", 60*60)

# Check which cells have partial NaN
partial_nan = np.any(np.isnan(thresholds), axis=0) & ~all_nan_cells
print("Cells with partial NaN:", partial_nan.sum())

# Check which cells have any NaN in target period
sst_target = np.load('sst_target.npy')
any_nan_target = np.any(np.isnan(sst_target), axis=0)
print("Cells with any NaN in target:", any_nan_target.sum())

# Check which cells have all NaN in target
all_nan_target = np.all(np.isnan(sst_target), axis=0)
print("Cells with all NaN in target:", all_nan_target.sum())
