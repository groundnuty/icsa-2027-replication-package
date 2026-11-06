
import numpy as np
import pandas as pd

# Load data
sst_data = np.load('/tmp/sst_data.npy')
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')
thresholds_smoothed = np.load('/tmp/thresholds_smoothed.npy')
climatology_smoothed = np.load('/tmp/climatology_smoothed.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

def date_to_doy(date):
    ts = pd.Timestamp(date)
    month, day = ts.month, ts.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

# Target period
target_start = np.datetime64('2022-06-01')
target_end = np.datetime64('2022-08-31')
target_mask = (time_sub >= target_start) & (time_sub <= target_end)
target_idx = np.where(target_mask)[0]

n_target = len(target_idx)
print("Target days:", n_target)

# Get DOY for each target day
target_doy = np.array([date_to_doy(pd.Timestamp(time_sub[i])) for i in target_idx])
print("Target DOYs:", target_doy)

# Get target SST data
target_sst = sst_data[target_idx]  # (n_target, n_lat, n_lon)
print("Target SST shape:", target_sst.shape)

# Get thresholds for target DOYs
target_thresholds = thresholds_smoothed[target_doy - 1]  # (n_target, n_lat, n_lon)
print("Target thresholds shape:", target_thresholds.shape)

# Hot days: SST >= threshold
hot = target_sst >= target_thresholds
print("Hot days shape:", hot.shape)
print("Number of hot cells-days:", hot.sum())

# For land cells (non-sea cells), they should be 0 (not hot)
hot = hot & sea_mask[np.newaxis, :, :]
print("After masking to sea cells, hot cells-days:", hot.sum())

# Now find per-cell MHWs
# For each cell, find runs of >=5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

n_lat, n_lon = sea_mask.shape

# For each cell, determine which days it's in an MHW
# mhw_cell: (n_target, n_lat, n_lon) boolean array
mhw_cell = np.zeros((n_target, n_lat, n_lon), dtype=bool)

for lat in range(n_lat):
    for lon in range(n_lon):
        if not sea_mask[lat, lon]:
            continue
        
        hot_cell = hot[:, lat, lon]  # (n_target,) boolean
        
        # Find runs of consecutive hot days
        # First, find hot runs
        runs = []  # list of (start, end) tuples (inclusive)
        i = 0
        while i < n_target:
            if hot_cell[i]:
                j = i
                while j < n_target and hot_cell[j]:
                    j += 1
                runs.append((i, j-1))
                i = j
            else:
                i += 1
        
        # Filter runs with length >= 5
        long_runs = [(s, e) for s, e in runs if (e - s + 1) >= 5]
        
        if not long_runs:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined_runs = [long_runs[0]]
        for s, e in long_runs[1:]:
            prev_s, prev_e = joined_runs[-1]
            gap = s - prev_e - 1
            if 1 <= gap <= 2:
                # Join
                joined_runs[-1] = (prev_s, e)
            else:
                joined_runs.append((s, e))
        
        # Mark MHW days
        for s, e in joined_runs:
            mhw_cell[s:e+1, lat, lon] = True

print("MHW cells-days:", mhw_cell.sum())

# Per-cell MHW days counts
mhw_per_cell = mhw_cell.sum(axis=0)
print("Cells with any MHW:", (mhw_per_cell > 0).sum())
print("MHW days per cell (max):", mhw_per_cell.max())
print("MHW days per cell (mean of cells with MHW):", mhw_per_cell[mhw_per_cell > 0].mean())

# Save intermediate
np.save('/tmp/mhw_cell.npy', mhw_cell)
np.save('/tmp/hot.npy', hot)
