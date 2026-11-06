
import numpy as np
import pandas as pd

thr_smooth = np.load('/work/thr_smooth.npy')
cli_smooth = np.load('/work/cli_smooth.npy')
target_arr = np.load('/work/target_arr.npy')
target_time = np.load('/work/target_time.npy').astype('datetime64[D]')

def date_to_doy(dt):
    d = pd.Timestamp(dt)
    month, day = d.month, d.day
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

nlat, nlon = target_arr.shape[1], target_arr.shape[2]
ntarget = target_arr.shape[0]

# Map each target date to its doy (1-366), then to index (0-365)
target_doy = np.array([date_to_doy(t) for t in target_time])
target_doy_idx = target_doy - 1
print("Target DOYs:", target_doy)

# Get threshold for each target day and each cell
# thresholds_for_target[d, i, j] = thr_smooth[target_doy_idx[d], i, j]
thr_for_target = thr_smooth[target_doy_idx, :, :]  # (ntarget, nlat, nlon)

# Determine hot days: SST >= threshold
# But need to be careful with NaN (land cells)
hot = np.zeros((ntarget, nlat, nlon), dtype=bool)
valid_sst = np.isfinite(target_arr)
hot = valid_sst & (target_arr >= thr_for_target)

print("Hot days count:", hot.sum())
print("Total target cells:", ntarget * nlat * nlon)

# Sea mask
sea_mask = np.all(valid_sst, axis=0)
print("Sea cells:", sea_mask.sum())

# For sea cells, determine per-cell MHWs
# A hot day in a cell: SST >= threshold
# A per-cell MHW: run of >= 5 consecutive hot days
# Runs separated by 1-2 non-hot days are joined

# Let me implement this per cell
# mhw_mask: (ntarget, nlat, nlon) - 1 if cell is inside a per-cell MHW on that day

mhw_mask = np.zeros((ntarget, nlat, nlon), dtype=np.uint8)

for i in range(nlat):
    for j in range(nlon):
        if not sea_mask[i, j]:
            continue
        
        # Get hot days for this cell
        hot_cell = hot[:, i, j]  # (ntarget,) boolean
        
        # Find runs of hot days
        # First identify hot runs
        runs = []  # list of (start_idx, end_idx) inclusive
        in_run = False
        run_start = 0
        
        for d in range(ntarget):
            if hot_cell[d] and not in_run:
                in_run = True
                run_start = d
            elif not hot_cell[d] and in_run:
                in_run = False
                runs.append((run_start, d-1))
        
        if in_run:
            runs.append((run_start, ntarget-1))
        
        if not runs:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        # First, only keep runs of length >= 5
        long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        if not long_runs:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined_runs = []
        current = long_runs[0]
        
        for next_run in long_runs[1:]:
            gap = next_run[0] - current[1] - 1  # number of non-hot days between
            if gap >= 1 and gap <= 2:
                # Join
                current = (current[0], next_run[1])
            else:
                joined_runs.append(current)
                current = next_run
        
        joined_runs.append(current)
        
        # Mark MHW days
        for start, end in joined_runs:
            mhw_mask[start:end+1, i, j] = 1

print("MHW mask count:", mhw_mask.sum())

np.save('/work/mhw_mask.npy', mhw_mask)
print("Saved")
