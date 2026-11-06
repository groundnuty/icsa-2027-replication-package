
import numpy as np
import datetime

# Load the data
baseline_sst = np.load('/tmp/baseline_sst.npy')
target_sst = np.load('/tmp/target_sst.npy')
baseline_times = np.load('/tmp/baseline_times.npy')
target_times = np.load('/tmp/target_times.npy')

print(f"Baseline shape: {baseline_sst.shape}")
print(f"Target shape: {target_sst.shape}")

# Convert numpy datetime64 to datetime.date
baseline_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in baseline_times]
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

# Identify sea cells: finite on all target days
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

print(f"Sea cells: {sea_mask.sum()} out of {n_lat*n_lon}")

# Find which cells are sea
sea_cells = np.argwhere(sea_mask)
print(f"Sea cell indices (lat, lon): {sea_cells[:10]}")
print(f"Sea cell indices (lat, lon) last few: {sea_cells[-10:]}")
