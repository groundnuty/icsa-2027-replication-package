
import numpy as np
import pandas as pd

# Load data
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
target_time = np.load('/work/target_time.npy', allow_pickle=True)
threshold_smooth = np.load('/work/threshold_smooth.npy')  # (366, 60, 60)
climatology_smooth = np.load('/work/climatology_smooth.npy')

tt = pd.to_datetime(target_time)
n_target, n_lat, n_lon = target_sst.shape

# Define doy mapping
cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def doy_from_md(m, d):
    return cum[m-1] + d

# Compute doy for each target day
target_doy = np.array([doy_from_md(t.month, t.day) for t in tt])
print("Target doy values:", target_doy[:5], "...", target_doy[-5:])

# For each target day and each cell, get the threshold
# threshold_smooth[doy-1, lat, lon]
# target_doy: array of 92 values

# Create hot array: (92, 60, 60) boolean
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)

for i in range(n_target):
    d_idx = target_doy[i] - 1  # 0-based index into threshold_smooth
    hot[i] = target_sst[i] >= threshold_smooth[d_idx]

print("Hot days per cell range:", hot.sum(axis=0).min(), "-", hot.sum(axis=0).max())

# Identify sea cells
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", sea_cells.sum())
