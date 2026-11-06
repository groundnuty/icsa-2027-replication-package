
import numpy as np
from datetime import date, timedelta

# Load data
baseline_data = np.load('/tmp/baseline_data.npy')
threshold_raw = np.load('/tmp/threshold_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')

print(f"Threshold shape: {threshold_raw.shape}")
print(f"Climatology shape: {climatology_raw.shape}")

# Check some values
# doy 153 = June 1
# Check a sea cell
# Let's check cell (30, 30) which is roughly center
print(f"Threshold doy 153, cell (30,30): {threshold_raw[152, 30, 30]}")
print(f"Climatology doy 153, cell (30,30): {climatology_raw[152, 30, 30]}")

# Check some NaN values (land cells)
# Find which cells are NaN in thresholds
nan_cells = np.isnan(threshold_raw[152])
print(f"NaN cells in threshold doy 153: {nan_cells.sum()} out of {nan_cells.size}")

# Check day 60 - it should be 0 now (we'll fill it later)
print(f"Day 60 threshold (before fill): {threshold_raw[59, 30, 30]}")
print(f"Day 60 climatology (before fill): {climatology_raw[59, 30, 30]}")
