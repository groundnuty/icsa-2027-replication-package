
import numpy as np
from datetime import date, timedelta

# Load all necessary data
target_sst = np.load('/tmp/target_sst.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
thr_smooth = np.load('/tmp/thr_smooth.npy')
cli_smooth = np.load('/tmp/cli_smooth.npy')

n_days, n_lat, n_lon = target_sst.shape
print(f"Target SST shape: {target_sst.shape}")
print(f"Sea cells: {sea_cells.sum()}")

# Day-of-year for each target date
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
cum_days = [0]
for md in month_days[:-1]:
    cum_days.append(cum_days[-1] + md)

def date_to_doy(d):
    return cum_days[d.month - 1] + d.day

target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

doy_values = np.array([date_to_doy(d) for d in target_dates])
print(f"Day of year range: {doy_values[0]} to {doy_values[-1]}")

# Compute hot mask for all cells: (n_days, n_lat, n_lon)
# hot[t, i, j] = target_sst[t, i, j] >= thr_smooth[doy_values[t]-1, i, j]
hot = np.zeros((n_days, n_lat, n_lon), dtype=bool)

for t in range(n_days):
    doy = doy_values[t]
    hot[t] = target_sst[t] >= thr_smooth[doy-1]

print(f"Hot mask shape: {hot.shape}")
print(f"Hot cells count: {hot.sum()}")

# For sea cells only (non-sea cells should have NaN in target_sst, and comparison with NaN gives False)
# So hot should already be False for non-sea cells
# Verify
sea_cells_2d = sea_cells  # (n_lat, n_lon)
print(f"Hot on sea cells: {np.sum(hot & sea_cells_2d[np.newaxis, :, :])}")
print(f"Hot on non-sea cells: {np.sum(hot & ~sea_cells_2d[np.newaxis, :, :])}")

# Now compute per-cell MHWs
# For each cell: find runs of at least 5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

# MHW mask: (n_days, n_lat, n_lon) - 1 if cell is inside a per-cell MHW on that day
mhw_mask = np.zeros((n_days, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        hot_cell = hot[:, i, j]  # (n_days,)
        
        # Find runs of hot days
        # Identify consecutive runs
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_days):
            if hot_cell[t]:
                if not in_run:
                    run_start = t
                    in_run = True
            else:
                if in_run:
                    runs.append((run_start, t - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_days - 1))
        
        # Keep only runs of at least 5 days
        runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        if not runs:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined_runs = [runs[0]]
        for r in runs[1:]:
            prev_s, prev_e = joined_runs[-1]
            curr_s, curr_e = r
            gap = curr_s - prev_e - 1
            if 1 <= gap <= 2:
                joined_runs[-1] = (prev_s, curr_e)  # merge
            else:
                joined_runs.append(r)
        
        # Mark MHW days
        for s, e in joined_runs:
            mhw_mask[s:e+1, i, j] = 1

print(f"MHW mask non-zero count: {mhw_mask.sum()}")

# Save
np.save('/tmp/mhw_mask.npy', mhw_mask)
np.save('/tmp/hot.npy', hot)
print("MHW mask saved")
