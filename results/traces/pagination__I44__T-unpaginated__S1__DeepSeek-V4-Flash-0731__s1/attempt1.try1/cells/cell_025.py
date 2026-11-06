import numpy as np
from datetime import date, timedelta
import pickle

# Reload data
target_sst = np.load('/tmp/work/target_sst.npy')
with open('/tmp/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
sea_cells = np.load('/tmp/work/sea_cells.npy')
threshold_smooth = np.load('/tmp/work/threshold_smooth.npy')
per_cell_mhw = np.load('/tmp/work/per_cell_mhw.npy')

n_target, n_lat, n_lon = target_sst.shape

def month_day_to_doy(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Find cells with non-contiguous hot runs that were joined
# First, let me recompute hot days
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for t in range(n_target):
    d = target_dates[t]
    doy = month_day_to_doy(d.month, d.day)
    thresh = threshold_smooth[doy-1]
    hot[t] = (target_sst[t] >= thresh) & sea_cells

# For each sea cell, find runs of hot days and check if any were joined
sea_idx = np.argwhere(sea_cells)
joined_cells = []

for si, (i, j) in enumerate(sea_idx):
    hot_cell = hot[:, i, j]
    
    # Find runs of consecutive hot days
    runs = []
    t = 0
    while t < n_target:
        if hot_cell[t]:
            start = t
            while t < n_target and hot_cell[t]:
                t += 1
            end = t - 1
            runs.append((start, end))
        else:
            t += 1
    
    # Filter to runs >= 5
    long_runs = [(s, e) for s, e in runs if (e - s + 1) >= 5]
    
    # Check if any long runs are separated by 1-2 days
    if len(long_runs) >= 2:
        for k in range(len(long_runs) - 1):
            gap = long_runs[k+1][0] - long_runs[k][1] - 1
            if 1 <= gap <= 2:
                joined_cells.append((i, j, long_runs[k], long_runs[k+1], gap))
                break

print(f"Cells with joined MHWs: {len(joined_cells)}")
for ic, jc, r1, r2, gap in joined_cells:
    print(f"  Cell ({ic},{jc}): run1={target_dates[r1[0]]} to {target_dates[r1[1]]}, run2={target_dates[r2[0]]} to {target_dates[r2[1]]}, gap={gap} days")
