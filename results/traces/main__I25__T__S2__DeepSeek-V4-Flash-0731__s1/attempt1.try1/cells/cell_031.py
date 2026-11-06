
import numpy as np
import pandas as pd
import os
import json

# Load saved intermediate results
threshold_smoothed = np.load('output/threshold_smoothed.npy')
sea_mask = np.load('output/sea_mask.npy')
target_sst_sea = np.load('output/target_sst_sea.npy')
target_time = np.load('output/target_time.npy')
lat_values = np.load('output/lat_values.npy')
lon_values = np.load('output/lon_values.npy')
target_doy = np.load('output/target_doy.npy')

n_target = len(target_doy)
n_sea = target_sst_sea.shape[1]

print(f"n_target: {n_target}, n_sea: {n_sea}")
print(f"Threshold shape: {threshold_smoothed.shape}")
print(f"Sea mask shape: {sea_mask.shape}")
print(f"Target DOY: {target_doy}")
print(f"Target time: {pd.Timestamp(target_time[0])} to {pd.Timestamp(target_time[-1])}")

# Compute hot matrix (comparison in float64)
hot = np.zeros((n_target, n_sea), dtype=bool)
target_sst_sea_f64 = target_sst_sea.astype(np.float64)
for i in range(n_target):
    doy = target_doy[i]
    hot[i, :] = target_sst_sea_f64[i, :] >= threshold_smoothed[doy-1, :]

print(f"Hot matrix: {hot.shape}, hot days: {hot.sum()}")

# Find per-cell MHWs (correct algorithm)
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
    
    # Initial MHWs: runs of >=5 consecutive hot days
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if not mhws:
        return np.zeros(n, dtype=bool)
    
    # Join MHWs separated by 1-2 non-hot days
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

# Compute per-cell MHW mask
mhw_sea = np.zeros((n_target, n_sea), dtype=bool)
for c in range(n_sea):
    mhw_sea[:, c] = find_cell_mhws_v2(hot[:, c])

print(f"Cells with MHWs: {(mhw_sea.sum(axis=0) > 0).sum()}")
print(f"Total MHW-days: {mhw_sea.sum()}")

# Regional events
active = mhw_sea.sum(axis=1) > 0
print(f"Active days: {active.sum()}")

# Find regional events
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

# Build mhw_full for all grid cells
mhw_full = np.zeros((n_target, sea_mask.shape[0], sea_mask.shape[1]), dtype=np.uint8)
sea_indices = np.where(sea_mask)
for i in range(n_sea):
    lat_i, lon_i = sea_indices[0][i], sea_indices[1][i]
    mhw_full[:, lat_i, lon_i] = mhw_sea[:, i]

print(f"mhw_full shape: {mhw_full.shape}")
print(f"mhw_full unique values: {np.unique(mhw_full)}")
print(f"mhw_full ones: {mhw_full.sum()}")
