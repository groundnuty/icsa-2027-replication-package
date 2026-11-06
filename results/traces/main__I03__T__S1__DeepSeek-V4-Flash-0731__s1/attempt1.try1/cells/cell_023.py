
import numpy as np
import datetime

# Load data
target_vals = np.load('target_vals.npy').astype(np.float64)
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
threshold_smooth = np.load('threshold_smooth.npy')
sea_cells = np.load('sea_cells.npy')

target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

def day_of_year(dt):
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month] + dt.day

target_doy = np.array([day_of_year(dt) for dt in target_dt])

ntarget = len(target_dt)
nlat, nlon = 60, 60

# Determine hot days
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

# Find per-cell MHWs
mhw_mask = np.zeros((ntarget, nlat, nlon), dtype=np.uint8)

for k in range(n_sea):
    lat_i, lon_i = sea_indices[0][k], sea_indices[1][k]
    hot_series = hot[:, lat_i, lon_i].astype(int)
    
    # Step 1: Find all maximal runs of hot days
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
    
    # Step 2: Identify MHWs as runs with length >= 5
    mhws = [r for r in runs if r[1] - r[0] + 1 >= 5]
    
    # Step 3: Join consecutive MHWs if gap (non-hot days between them) is 1 or 2
    # This is iterative
    changed = True
    while changed and len(mhws) > 1:
        changed = False
        new_mhws = []
        i = 0
        while i < len(mhws):
            if i < len(mhws) - 1:
                # Count non-hot days between mhws[i] and mhws[i+1]
                # The gap is the days between end of mhws[i] and start of mhws[i+1]
                gap_start = mhws[i][1] + 1
                gap_end = mhws[i+1][0] - 1
                if gap_start <= gap_end:
                    # Count non-hot days in gap
                    non_hot_count = (1 - hot_series[gap_start:gap_end+1]).sum()
                else:
                    non_hot_count = 0
                
                if 1 <= non_hot_count <= 2:
                    # Join
                    new_mhws.append([mhws[i][0], mhws[i+1][1]])
                    i += 2
                    changed = True
                    continue
            new_mhws.append(mhws[i])
            i += 1
        mhws = new_mhws
    
    # Mark MHW days
    for start, end in mhws:
        mhw_mask[start:end+1, lat_i, lon_i] = 1

print(f"MHW mask sum: {mhw_mask.sum()}")
print(f"Cells with any MHW: {(mhw_mask.sum(axis=0) > 0)[sea_cells].sum()}")

# Save
np.save('mhw_mask_per_cell.npy', mhw_mask)
