
import numpy as np
import pandas as pd

# Load data
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')
target_data = np.load('/work/target_data.npy')
sea_cells = np.load('/work/sea_cells.npy')

print(f"Target data shape: {target_data.shape}")
print(f"Thresholds shape: {thresholds_smooth.shape}")
print(f"Sea cells: {sea_cells.sum()}")

# Define doy function
def doy(month, day):
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

# Target dates
target_start = pd.Timestamp('2004-06-01')
target_end = pd.Timestamp('2004-08-31')
target_dates = pd.date_range(target_start, target_end, freq='D')

# Compute doy for each target date
target_doys = np.array([doy(dt.month, dt.day) for dt in target_dates])
print(f"Target doys: {target_doys[0]} to {target_doys[-1]}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}")

# For each target day and cell, check if hot
# target_data: (92, 60, 60)
# thresholds_smooth: (60, 60, 366) indexed by [lat, lon, doy-1]
n_time = len(target_dates)
n_lat, n_lon = sea_cells.shape

# For each target day, get the smoothed threshold for that doy for each cell
# thresholds_smooth[:, :, target_doys[t]-1] gives (60, 60) for each t
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    d_idx = target_doys[t] - 1  # 0-indexed
    thresh = thresholds_smooth[:, :, d_idx]
    hot[t] = target_data[t] >= thresh

print(f"Hot cells per day (first 5): {hot[:5].sum(axis=(1,2))}")
print(f"Total hot cell-days: {hot.sum()}")

# Now find per-cell MHWs
# For each sea cell, find runs of >= 5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

# mhw_mask: same shape as target_data, 1 where cell is inside a per-cell MHW
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

for lat_i in range(n_lat):
    for lon_i in range(n_lon):
        if not sea_cells[lat_i, lon_i]:
            continue
        
        # Get hot pattern for this cell
        hot_cell = hot[:, lat_i, lon_i]  # shape (n_time,)
        
        # Find runs of hot days
        runs = []
        in_run = False
        run_start = 0
        
        for t in range(n_time):
            if hot_cell[t] and not in_run:
                in_run = True
                run_start = t
            elif not hot_cell[t] and in_run:
                in_run = False
                runs.append((run_start, t-1))
        if in_run:
            runs.append((run_start, n_time-1))
        
        # Filter runs of at least 5 consecutive hot days
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Join runs separated by 1-2 non-hot days
        if len(mhw_runs) > 1:
            joined = []
            current = mhw_runs[0]
            for next_run in mhw_runs[1:]:
                gap = next_run[0] - current[1] - 1
                if gap <= 2:
                    # Join
                    current = (current[0], next_run[1])
                else:
                    joined.append(current)
                    current = next_run
            joined.append(current)
            mhw_runs = joined
        
        # Mark mask
        for run_start, run_end in mhw_runs:
            mhw_mask[run_start:run_end+1, lat_i, lon_i] = 1

print(f"MHW mask: {mhw_mask.sum()} cell-days in MHWs")
print(f"MHW cells per day (first 10): {mhw_mask[:10].sum(axis=(1,2))}")

# Save
np.save('/work/mhw_mask.npy', mhw_mask)
print("Saved MHW mask")
