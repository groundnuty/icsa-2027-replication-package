
import numpy as np
from datetime import datetime

# Load target data
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
target_times = np.load('/work/target_times.npy')

# Sea cells: cells where SST is finite on every day of the target period
sea_cells = np.all(np.isfinite(target_sst), axis=0)  # (60, 60) boolean
print("Sea cells:", sea_cells.sum(), "out of", sea_cells.size)

# Also check how many cells have some NaN
some_nan = np.any(np.isnan(target_sst), axis=0)
print("Cells with any NaN in target:", some_nan.sum())

# Check base data NaN counts for those cells
base_sst = np.load('/work/base_sst.npy')
# For sea cells, check NaN fraction in baseline
nan_frac = np.mean(np.isnan(base_sst[:, sea_cells]), axis=0)
print("NaN fraction in baseline for sea cells: min={:.6f}, max={:.6f}".format(nan_frac.min(), nan_frac.max()))
