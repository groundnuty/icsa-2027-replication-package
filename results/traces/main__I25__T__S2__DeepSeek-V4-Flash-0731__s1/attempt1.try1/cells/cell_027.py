
import numpy as np
import pandas as pd
import os

# Reload data
threshold_smoothed = np.load('output/threshold_smoothed.npy')
target_sst_sea = np.load('output/target_sst_sea.npy')
target_time = np.load('output/target_time.npy')
target_doy = np.load('output/target_doy.npy')

n_target = len(target_doy)
n_sea = target_sst_sea.shape[1]

# Compute hot matrix
hot = np.zeros((n_target, n_sea), dtype=bool)
for i in range(n_target):
    doy = target_doy[i]
    hot[i, :] = target_sst_sea[i, :] >= threshold_smoothed[doy-1, :]

# Check hot patterns for the first 20 days
print("First 20 days - number of hot cells:")
for i in range(20):
    print(f"  Day {i}: {pd.Timestamp(target_time[i]).strftime('%Y-%m-%d')}, hot cells: {hot[i].sum()}, "
          f"SST range: [{np.nanmin(target_sst_sea[i]):.2f}, {np.nanmax(target_sst_sea[i]):.2f}]")

# Check if the first 5 days have ≥5 consecutive hot days in any cell
print("\nCells with hot days in first 5 days (June 1-5):")
first5_hot = hot[:5].all(axis=0)
print(f"  Cells hot on ALL of first 5 days: {first5_hot.sum()}")
first6_hot = hot[:6].all(axis=0)
print(f"  Cells hot on ALL of first 6 days: {first6_hot.sum()}")

# Check how many cells have MHWs starting on day 0
# An MHW starts on day 0 if there's a run of ≥5 hot days starting at day 0
# Let's check the hot pattern for a few cells
print("\nHot patterns for first 10 cells (days 0-14):")
for c in range(10):
    pattern = ''.join(['H' if hot[i, c] else '.' for i in range(15)])
    print(f"  Cell {c}: {pattern}")

# Check overall hot pattern
print("\nTotal hot cells per day:")
for i in range(n_target):
    print(f"  Day {i} ({pd.Timestamp(target_time[i]).strftime('%m-%d')}): {hot[i].sum()}")
