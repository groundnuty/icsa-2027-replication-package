
import numpy as np
import os

# Reload data
threshold_smoothed = np.load('output/threshold_smoothed.npy')
sea_mask = np.load('output/sea_mask.npy')
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
    """Correct algorithm:
    1. Find runs of ≥5 consecutive hot days → MHWs
    2. Join MHWs separated by 1-2 non-hot days
    Returns a boolean array where True means the day is inside a per-cell MHW."""
    n = len(hot_series)
    
    # Find all runs of hot days
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
    
    # Identify initial MHWs (runs of ≥5 hot days)
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if not mhws:
        return np.zeros(n, dtype=bool)
    
    # Join MHWs separated by 1-2 non-hot days
    joined_mhws = [list(mhws[0])]
    for mhw in mhws[1:]:
        gap = mhw[0] - joined_mhws[-1][1] - 1
        if 1 <= gap <= 2:
            # Join
            joined_mhws[-1][1] = mhw[1]
        else:
            joined_mhws.append(list(mhw))
    
    # Mark days inside joined MHWs
    inside_mhw = np.zeros(n, dtype=bool)
    for mhw in joined_mhws:
        inside_mhw[mhw[0]:mhw[1]+1] = True
    
    return inside_mhw

# Recompute per-cell MHW mask
print("Finding per-cell MHWs (corrected)...")
mhw_sea = np.zeros((n_target, n_sea), dtype=bool)
for c in range(n_sea):
    mhw_sea[:, c] = find_cell_mhws_v2(hot[:, c])

print(f"Cells with MHWs: {(mhw_sea.sum(axis=0) > 0).sum()}")
print(f"Total MHW-days (cell-days): {mhw_sea.sum()}")

# Regional events
active = mhw_sea.sum(axis=1) > 0
print(f"Active days: {active.sum()} out of {n_target}")

events = []
i = 0
while i < n_target:
    if active[i]:
        start = i
        while i < n_target and active[i]:
            i += 1
        events.append((start, i - 1))
    else:
        i += 1

print(f"Regional events: {len(events)}")
for onset_idx, end_idx in events:
    onset = pd.Timestamp(target_time[onset_idx]).strftime('%Y-%m-%d')
    end = pd.Timestamp(target_time[end_idx]).strftime('%Y-%m-%d')
    print(f"  Event: {onset} to {end}")
