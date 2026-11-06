
import numpy as np
import datetime
import pickle

# Load data
target_sst = np.load('work/target_sst.npy')
sea_mask = np.load('work/sea_mask.npy')
threshold_smooth = np.load('work/threshold_smooth.npy')

print(f"Target SST: {target_sst.shape}")
print(f"Sea mask: {sea_mask.shape}, sea cells: {sea_mask.sum()}")
print(f"Threshold smooth: {threshold_smooth.shape}")

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

# Target dates
target_start = datetime.date(2012, 6, 1)
target_end = datetime.date(2012, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)

# Day of year for each target date
target_doy = np.array([doy_from_date(date) for date in target_dates])
print(f"Target DOY: {target_doy}")

# For each cell, get the threshold for each target day
# threshold_smooth: (366, 3600) - indexed by doy-1
n_target = len(target_dates)
n_cells = 3600
n_lat, n_lon = 60, 60

# Reshape threshold to (366, n_lat, n_lon)
threshold_3d = threshold_smooth.reshape(366, n_lat, n_lon)

# For each target day, get the threshold for each cell
# target_doy: (92,)
# threshold_for_target: (92, n_lat, n_lon)
threshold_for_target = threshold_3d[target_doy - 1]  # subtract 1 for 0-indexing

# Determine hot days
# hot: (92, n_lat, n_lon) boolean
hot = target_sst >= threshold_for_target
hot_land = np.copy(hot)
hot_land[~sea_mask] = False  # Land cells are never hot

print(f"Hot days total: {hot_land.sum()}")
print(f"Hot fraction (sea cells): {hot_land[sea_mask].mean():.4f}")

# Now find per-cell MHWs
# For each cell: 
# 1. Find runs of >=5 consecutive hot days
# 2. Join runs separated by 1-2 non-hot days

# Let's implement this per cell
n_lat, n_lon = 60, 60
cell_mhw = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        hot_days = hot_land[:, i, j]
        
        # First find runs of >=5 consecutive hot days
        # Then join runs separated by 1-2 non-hot days
        
        # Step 1: Identify all hot runs
        # We need to first identify hot runs, then join gaps
        
        # Approach: iterative joining
        # First mark all hot days
        mhw_mask = hot_days.copy()
        
        # Find runs of consecutive hot days (including gaps of 1-2 to be joined later)
        # First, let's identify runs of >=5 consecutive hot days
        # Then join runs separated by 1-2 non-hot days
        
        # Strategy: 
        # 1. Mark all hot days
        # 2. Find maximal runs of hot days
        # 3. For runs separated by 1-2 non-hot days, merge them
        
        # Find runs of hot days
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_target):
            if hot_days[t]:
                if not in_run:
                    in_run = True
                    run_start = t
            else:
                if in_run:
                    runs.append((run_start, t - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_target - 1))
        
        if len(runs) == 0:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined_runs = []
        current = list(runs[0])
        for next_run in runs[1:]:
            gap = next_run[0] - current[1] - 1
            if gap <= 2:
                # Join
                current[1] = next_run[1]
            else:
                joined_runs.append(tuple(current))
                current = list(next_run)
        joined_runs.append(tuple(current))
        
        # Filter runs of length >= 5
        for run_start, run_end in joined_runs:
            if run_end - run_start + 1 >= 5:
                cell_mhw[run_start:run_end+1, i, j] = 1

print(f"Cells with MHWs: {(cell_mhw.any(axis=0)).sum()}")
print(f"Total cell-MHW days: {cell_mhw.sum()}")

# Save per-cell MHW mask
np.save('work/cell_mhw.npy', cell_mhw)
print("Saved cell MHW mask")
