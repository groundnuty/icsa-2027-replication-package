
import numpy as np
import pandas as pd

# Load data
sst_data = np.load('/tmp/sst_data.npy')
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')
thresholds_raw = np.load('/tmp/thresholds_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Check NaN in thresholds for sea cells across target DOYs (153-244)
target_doy_range = range(153, 245)
nan_count = 0
for d in target_doy_range:
    idx = d - 1
    nan_count += np.isnan(thresholds_raw[idx][sea_mask]).sum()
print(f"NaN in thresholds for sea cells across target DOYs: {nan_count}")

# Check NaN in climatology for sea cells across all DOYs
nan_count_all = 0
for d in range(1, 367):
    idx = d - 1
    nan_count_all += np.isnan(climatology_raw[idx][sea_mask]).sum()
print(f"NaN in climatology for sea cells across all DOYs: {nan_count_all}")

# Check NaN in thresholds for sea cells across all DOYs
nan_count_all_t = 0
for d in range(1, 367):
    idx = d - 1
    nan_count_all_t += np.isnan(thresholds_raw[idx][sea_mask]).sum()
print(f"NaN in thresholds for sea cells across all DOYs: {nan_count_all_t}")

# How many sea cells have any NaN in thresholds?
sea_idx = np.where(sea_mask)
nan_in_thresh_per_cell = np.zeros(sea_mask.shape, dtype=bool)
for d in range(1, 367):
    if d == 60:
        continue
    nan_in_thresh_per_cell |= np.isnan(thresholds_raw[d-1])
print(f"Sea cells with any NaN in thresholds: {(nan_in_thresh_per_cell & sea_mask).sum()}")
