
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

# Check active days
active = mhw_sea.sum(axis=1) > 0
print("Active days:")
for i in range(n_target):
    if active[i]:
        print(f"  Day {i}: {pd.Timestamp(target_time[i]).strftime('%Y-%m-%d')} - {mhw_sea[i].sum()} cells in MHW")

print(f"\nTotal active days: {active.sum()}")

# Check: on day 18, is any cell in an MHW?
print(f"Day 18 (June 19): {mhw_sea[18].sum()} cells in MHW")
print(f"Day 19 (June 20): {mhw_sea[19].sum()} cells in MHW")
print(f"Day 20 (June 21): {mhw_sea[20].sum()} cells in MHW")
print(f"Day 21 (June 22): {mhw_sea[21].sum()} cells in MHW")
print(f"Day 22 (June 23): {mhw_sea[22].sum()} cells in MHW")
print(f"Day 23 (June 24): {mhw_sea[23].sum()} cells in MHW")
print(f"Day 24 (June 25): {mhw_sea[24].sum()} cells in MHW")
