
import numpy as np
import datetime

# Load data
target_vals = np.load('target_vals.npy').astype(np.float64)  # (92, 60, 60)
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
threshold_smooth = np.load('threshold_smooth.npy')  # (367, 60, 60)
sea_cells = np.load('sea_cells.npy')

target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

def day_of_year(dt):
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month] + dt.day

target_doy = np.array([day_of_year(dt) for dt in target_dt])

# For each sea cell, determine hot days
ntarget = len(target_dt)
nlat, nlon = 60, 60

# hot: (ntarget, nlat, nlon) - True if SST >= threshold for that day
hot = np.zeros((ntarget, nlat, nlon), dtype=bool)

sea_indices = np.where(sea_cells)
n_sea = len(sea_indices[0])

for k in range(n_sea):
    lat_i, lon_i = sea_indices[0][k], sea_indices[1][k]
    for t in range(ntarget):
        doy = target_doy[t]
        sst = target_vals[t, lat_i, lon_i]
        thresh = threshold_smooth[doy, lat_i, lon_i]
        hot[t, lat_i, lon_i] = sst >= thresh

print(f"Hot days per cell: {hot.sum(axis=0)[sea_cells].min()} to {hot.sum(axis=0)[sea_cells].max()}")

# Find per-cell MHWs
# A per-cell MHW is a run of >=5 consecutive hot days
# Per-cell MHWs separated by 1-2 non-hot days are joined

# Initialize mask for being inside a per-cell MHW
mhw_mask = np.zeros((ntarget, nlat, nlon), dtype=np.uint8)

for k in range(n_sea):
    lat_i, lon_i = sea_indices[0][k], sea_indices[1][k]
    hot_series = hot[:, lat_i, lon_i].astype(int)
    
    # Find runs of hot days
    # First, find all runs of hot days (consecutive)
    runs = []
    i = 0
    while i < ntarget:
        if hot_series[i] == 1:
            start = i
            while i < ntarget and hot_series[i] == 1:
                i += 1
            end = i - 1
            runs.append([start, end])
        else:
            i += 1
    
    # Join runs separated by 1-2 non-hot days
    # Iteratively merge
    changed = True
    while changed and len(runs) > 1:
        changed = False
        new_runs = []
        i = 0
        while i < len(runs):
            if i < len(runs) - 1:
                gap = runs[i+1][0] - runs[i][1] - 1
                if 1 <= gap <= 2:
                    # Merge
                    new_runs.append([runs[i][0], runs[i+1][1]])
                    i += 2
                    changed = True
                    continue
            new_runs.append(runs[i])
            i += 1
        runs = new_runs
    
    # Filter runs with length >= 5
    for start, end in runs:
        length = end - start + 1
        if length >= 5:
            mhw_mask[start:end+1, lat_i, lon_i] = 1

print(f"MHW mask sum: {mhw_mask.sum()}")
print(f"Cells with any MHW: {(mhw_mask.sum(axis=0) > 0)[sea_cells].sum()}")

# Save
np.save('mhw_mask_per_cell.npy', mhw_mask)
