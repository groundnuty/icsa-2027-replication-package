
import numpy as np
import pandas as pd

sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')
thresholds_smoothed = np.load('/tmp/thresholds_smoothed.npy')

# Target period
times_np = times.values
target_start = np.datetime64('2015-06-01')
target_end = np.datetime64('2015-08-31')
target_mask = (times_np >= target_start) & (times_np <= target_end)
target_indices = np.where(target_mask)[0]
n_target = len(target_indices)

# Sea cells
target_sst = sst_data[target_indices, :, :]
finite_all = np.all(np.isfinite(target_sst), axis=0)
sea_cells = np.argwhere(finite_all)
n_sea = len(sea_cells)

def compute_doy(month, day):
    if month == 1:
        return day
    elif month == 2:
        return 31 + day
    else:
        days_before = 60
        days_in_month = {3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
        for m in range(3, month):
            days_before += days_in_month[m]
        return days_before + day

# Get doy for each target day
target_doy = np.array([compute_doy(times[i].month, times[i].day) for i in target_indices])

# For each sea cell, determine hot days
# hot[cell_idx, target_day_idx] = 1 if hot, 0 otherwise
hot = np.zeros((n_sea, n_target), dtype=np.int8)

for ci, (lat, lon) in enumerate(sea_cells):
    sst_cell = sst_data[target_indices, lat, lon]
    thresh_cell = thresholds_smoothed[target_doy - 1, lat, lon]
    hot[ci, :] = (sst_cell >= thresh_cell).astype(np.int8)

print("Hot days computed. Shape:", hot.shape)
print("Fraction of hot days:", hot.mean())

# Find per-cell MHWs
# A per-cell MHW is a run of at least 5 consecutive hot days
# MHWs separated by 1 or 2 non-hot days are joined

# For each cell, find MHW mask (1 if in a per-cell MHW, 0 otherwise)
mhw_mask = np.zeros((n_sea, n_target), dtype=np.int8)

for ci in range(n_sea):
    h = hot[ci, :]
    # Find runs of hot days
    # First, find runs of >= 5 consecutive hot days
    # Then join runs separated by 1 or 2 non-hot days
    
    # Step 1: find contiguous hot runs
    runs = []
    i = 0
    while i < n_target:
        if h[i] == 1:
            j = i
            while j < n_target and h[j] == 1:
                j += 1
            runs.append((i, j - 1))  # inclusive
            i = j
        else:
            i += 1
    
    # Step 2: keep only runs of length >= 5
    long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    
    # Step 3: join runs separated by 1 or 2 non-hot days
    if len(long_runs) > 0:
        joined = [list(long_runs[0])]
        for r in long_runs[1:]:
            gap = r[0] - joined[-1][1] - 1
            if 1 <= gap <= 2:
                joined[-1][1] = r[1]
            else:
                joined.append(list(r))
        
        # Mark MHW days
        for start, end in joined:
            mhw_mask[ci, start:end+1] = 1

print("MHW mask computed. Total MHW cell-days:", mhw_mask.sum())
print("Fraction of cell-days in MHW:", mhw_mask.mean())

# Save
np.save('/tmp/mhw_mask.npy', mhw_mask)
np.save('/tmp/sea_cells.npy', sea_cells)
np.save('/tmp/target_indices.npy', target_indices)
print("Saved MHW mask and sea cells")
