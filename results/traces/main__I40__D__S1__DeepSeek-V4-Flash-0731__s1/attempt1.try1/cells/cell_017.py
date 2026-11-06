
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load data
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')
base_times = np.load('/work/base_times.npy')
targ_times = np.load('/work/targ_times.npy')
thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')

base_dates = pd.DatetimeIndex(base_times)
targ_dates = pd.DatetimeIndex(targ_times)

n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
n_targ = len(targ_dates)

print(f"Target period: {targ_dates[0]} to {targ_dates[-1]}, {n_targ} days")
print(f"Grid: {n_lat} x {n_lon}")

# Step 1: Sea cells - cells with finite SST on every day of target period
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        if np.all(np.isfinite(target_sst[:, i, j])):
            sea_cells[i, j] = True

print(f"Sea cells: {sea_cells.sum()} out of {n_lat * n_lon}")

# Check which cells are sea vs land
print(f"Target SST NaN pattern (first 10 days, first 10 lat, first 10 lon):")
print(np.isnan(target_sst[:10, :10, :10]).sum())

# For sea cells, check if thresholds are NaN
sea_nan_threshold = 0
for i in range(n_lat):
    for j in range(n_lon):
        if sea_cells[i, j]:
            if np.isnan(thresholds[:, i, j]).any():
                sea_nan_threshold += 1
print(f"Sea cells with NaN in threshold: {sea_nan_threshold}")
