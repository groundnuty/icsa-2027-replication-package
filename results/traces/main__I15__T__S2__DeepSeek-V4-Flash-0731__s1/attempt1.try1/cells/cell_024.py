
import numpy as np

# hot_mask: (time, lat, lon) boolean
hot_mask = None  # will recompute

# Recompute with proper handling
sst_target = np.load('sst_target.npy')
threshold_smooth = np.load('threshold_smooth.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')
import pandas as pd
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

target_doy = np.array([day_of_year(d) for d in target_dates])

sea_cells = np.all(~np.isnan(sst_target), axis=0)
n_time, n_lat, n_lon = sst_target.shape

hot_mask = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    thr = threshold_smooth[doy]
    valid = ~np.isnan(sst_target[t]) & ~np.isnan(thr) & sea_cells
    hot_mask[t] = valid & (sst_target[t] >= thr)

print('Hot mask computed.')

# For each sea cell, find per-cell MHWs
# per_cell_mhw: (time, lat, lon) boolean, 1 if the cell is in a per-cell MHW on that day
per_cell_mhw = np.zeros_like(hot_mask, dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        hot = hot_mask[:, i, j]  # (n_time,)
        
        # Find runs of consecutive hot days
        # First, find all maximal runs of hot days
        runs = []  # list of (start, end) indices
        in_run = False
        for t in range(n_time):
            if hot[t]:
                if not in_run:
                    run_start = t
                    in_run = True
            else:
                if in_run:
                    runs.append((run_start, t - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_time - 1))
        
        # Filter runs with length >= 5
        long_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Join runs separated by 1-2 non-hot days
        if not long_runs:
            continue
        
        joined = [long_runs[0]]
        for run in long_runs[1:]:
            prev_end = joined[-1][1]
            gap = run[0] - prev_end - 1
            if gap <= 2:
                # Join: extend previous to include the gap and this run
                joined[-1] = (joined[-1][0], run[1])
            else:
                joined.append(run)
        
        # Mark per-cell MHW days
        for start, end in joined:
            per_cell_mhw[start:end+1, i, j] = True

print('Per-cell MHW days:', per_cell_mhw.sum())
# Save
np.save('per_cell_mhw.npy', per_cell_mhw)
np.save('sea_cells.npy', sea_cells)
