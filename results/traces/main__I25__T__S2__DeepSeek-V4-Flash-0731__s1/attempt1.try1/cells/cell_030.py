
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

# Compute MHWs
mhw_sea = np.zeros((n_target, n_sea), dtype=bool)
for c in range(n_sea):
    mhw_sea[:, c] = find_cell_mhws_v2(hot[:, c])

# Check which cells are in MHW on day 17
cells_day17 = np.where(mhw_sea[17])[0]
print(f"Cells in MHW on day 17 (June 18): {cells_day17}")
for c in cells_day17:
    # Find the MHW period for this cell
    mhw_days = np.where(mhw_sea[:, c])[0]
    print(f"  Cell {c}: MHW from day {mhw_days[0]} to day {mhw_days[-1]}")
    # Hot pattern around this period
    pattern = ''.join(['H' if hot[i, c] else '.' for i in range(10, 25)])
    print(f"    Hot pattern (days 10-24): {pattern}")

# Also check day 16 and 15
for day in [15, 16]:
    cells = np.where(mhw_sea[day])[0]
    print(f"\nCells in MHW on day {day}: {cells}")
    for c in cells:
        mhw_days = np.where(mhw_sea[:, c])[0]
        print(f"  Cell {c}: MHW from day {mhw_days[0]} to day {mhw_days[-1]}")
