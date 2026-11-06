
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import os

# Load saved intermediate results
threshold_smoothed = np.load('output/threshold_smoothed.npy')
climatology_smoothed = np.load('output/climatology_smoothed.npy')
sea_mask = np.load('output/sea_mask.npy')
target_sst_sea = np.load('output/target_sst_sea.npy')
target_sst_full = np.load('output/target_sst_full.npy')
target_time = np.load('output/target_time.npy')
lat_values = np.load('output/lat_values.npy')
lon_values = np.load('output/lon_values.npy')
target_doy = np.load('output/target_doy.npy')

print(f"Threshold smoothed: {threshold_smoothed.shape}")
print(f"Target SST (sea): {target_sst_sea.shape}")
print(f"Target DOY: {target_doy}")
print(f"Target time range: {target_time[0]} to {target_time[-1]}")

# =====================
# Find per-cell MHWs in target period
# =====================
# A day is hot in a cell if SST >= threshold for that day of year
# Day of year for target dates: target_doy[i] for day i

# Get threshold for each target day for each sea cell
# threshold_smoothed[doy-1, cell] gives the threshold
n_target = len(target_doy)
n_sea = target_sst_sea.shape[1]

hot = np.zeros((n_target, n_sea), dtype=bool)
for i in range(n_target):
    doy = target_doy[i]
    hot[i, :] = target_sst_sea[i, :] >= threshold_smoothed[doy-1, :]

print(f"Hot matrix shape: {hot.shape}")
print(f"Hot days per cell (first 5 cells): {hot.sum(axis=0)[:5]}")
print(f"Cells with at least one hot day: {(hot.sum(axis=0) > 0).sum()}")

# =====================
# Find per-cell MHWs
# A per-cell MHW is a run of at least 5 consecutive hot days
# Per-cell MHWs separated by 1 or 2 non-hot days are joined, and gap days belong to them
# =====================

def find_cell_mhws(hot_series):
    """Find per-cell MHWs in a binary hot series.
    Returns a boolean array of length len(hot_series) where True means the day
    is inside a per-cell MHW."""
    n = len(hot_series)
    inside_mhw = np.zeros(n, dtype=bool)
    
    # Find runs of hot days
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
    
    if not runs:
        return inside_mhw
    
    # Join runs separated by 1 or 2 non-hot days
    joined_runs = [list(runs[0])]
    for run in runs[1:]:
        gap = run[0] - joined_runs[-1][1] - 1
        if gap <= 2:
            # Join
            joined_runs[-1][1] = run[1]
        else:
            joined_runs.append(list(run))
    
    # Keep only runs of at least 5 days (after joining, gap days count as part of the MHW)
    for run in joined_runs:
        if run[1] - run[0] + 1 >= 5:
            inside_mhw[run[0]:run[1]+1] = True
    
    return inside_mhw

# Compute per-cell MHW mask
print("Finding per-cell MHWs...")
mhw_sea = np.zeros((n_target, n_sea), dtype=bool)
for c in range(n_sea):
    mhw_sea[:, c] = find_cell_mhws(hot[:, c])

print(f"Cells with MHWs: {(mhw_sea.sum(axis=0) > 0).sum()}")
print(f"Total MHW-days (cell-days): {mhw_sea.sum()}")

# =====================
# Aggregate to regional events
# =====================
# A day is active if at least one sea cell is inside a per-cell MHW
active = mhw_sea.sum(axis=1) > 0
print(f"Active days: {active.sum()} out of {n_target}")

# Find regional MHW events (maximal runs of consecutive active days)
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

# =====================
# Build output
# =====================

# mhw_mask: (time, lat, lon) uint8, 1 where cell is inside per-cell MHW
# Land cells are 0
mhw_full = np.zeros((n_target, sea_mask.shape[0], sea_mask.shape[1]), dtype=np.uint8)
# Map sea cell index back to (lat, lon)
sea_indices = np.where(sea_mask)
for i in range(n_sea):
    lat_i, lon_i = sea_indices[0][i], sea_indices[1][i]
    mhw_full[:, lat_i, lon_i] = mhw_sea[:, i]

print(f"mhw_full shape: {mhw_full.shape}")

# Save the mhw mask and other info for later
np.save('output/mhw_full.npy', mhw_full)
np.save('output/active.npy', active)

# Report info
events_list = []
for onset_idx, end_idx in events:
    onset = pd.Timestamp(target_time[onset_idx]).strftime('%Y-%m-%d')
    end = pd.Timestamp(target_time[end_idx]).strftime('%Y-%m-%d')
    events_list.append({"onset": onset, "end": end})

print("\nFinal events:")
for e in events_list:
    print(f"  {e['onset']} to {e['end']}")
