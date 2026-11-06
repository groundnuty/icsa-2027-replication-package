
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

def find_cell_mhws_v2(hot_series):
    n = len(hot_series)
    runs = []
    i = 0
    while i < n:
        if hot_series[i]:
            start = i
            while i < n and hot_series[i]:
                i += 1
            runs.append((start, i - 1))
        else:
            i += 1
    
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if not mhws:
        return np.zeros(n, dtype=bool)
    
    joined_mhws = [list(mhws[0])]
    for mhw in mhws[1:]:
        gap = mhw[0] - joined_mhws[-1][1] - 1
        if 1 <= gap <= 2:
            joined_mhws[-1][1] = mhw[1]
        else:
            joined_mhws.append(list(mhw))
    
    inside_mhw = np.zeros(n, dtype=bool)
    for mhw in joined_mhws:
        inside_mhw[mhw[0]:mhw[1]+1] = True
    
    return inside_mhw

# Check which cells are hot around days 48-56 (July 19-27)
print("Hot cells around July 19-27 (days 48-56):")
for i in range(48, 57):
    print(f"  Day {i} ({pd.Timestamp(target_time[i]).strftime('%m-%d')}): {hot[i].sum()} hot cells")

# Check for cells with hot patterns in this period
print("\nHot patterns for days 48-56 for cells that have any hot day there:")
cells_with_hot = np.where(hot[48:57].sum(axis=0) > 0)[0]
print(f"Cells with hot days in this period: {len(cells_with_hot)}")
for c in cells_with_hot[:20]:
    pattern = ''.join(['H' if hot[i, c] else '.' for i in range(48, 57)])
    print(f"  Cell {c}: {pattern}")

# Now check if these cells have MHWs spanning this period
# Let's compute MHW for a few cells
for c in cells_with_hot[:5]:
    mhw = find_cell_mhws_v2(hot[:, c])
    # Find which days this cell is in an MHW
    mhw_days = np.where(mhw)[0]
    if len(mhw_days) > 0:
        print(f"\nCell {c}: MHW on days {mhw_days[0]} to {mhw_days[-1]}")
        # Show the hot pattern in days 45-60
        pattern = ''.join(['H' if hot[i, c] else '.' for i in range(45, 61)])
        print(f"  Hot pattern (days 45-60): {pattern}")
        pattern2 = ''.join(['M' if mhw[i] else '.' for i in range(45, 61)])
        print(f"  MHW pattern (days 45-60): {pattern2}")
