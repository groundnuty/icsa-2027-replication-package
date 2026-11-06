
import numpy as np
import datetime

# Load data
target_sst = np.load('/tmp/target_sst.npy')       # (92, 60, 60)
target_times = np.load('/tmp/target_times.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')  # (366, 60, 60)
climatology_smooth = np.load('/tmp/climatology_smooth.npy')

target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Compute day-of-year for each target day
target_doy = np.array([day_of_year(d) for d in target_dates])
print(f"Target day-of-years: {target_doy}")
print(f"Target dates: {target_dates[:5]} to {target_dates[-5:]}")

# For each sea cell, compute which days are hot
n_time, n_lat, n_lon = target_sst.shape

# Identify sea cells
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# Get the threshold for each target day and each cell
# threshold_smooth has shape (366, 60, 60)
# For each target day, get the threshold for the corresponding day-of-year

# Create hot_mask: (n_time, n_lat, n_lon) where 1 if hot, 0 otherwise
hot_mask = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    doy = target_doy[t]
    thresh = threshold_smooth[doy-1, :, :]  # (60, 60)
    sst = target_sst[t, :, :]
    hot_mask[t] = (sst >= thresh) & np.isfinite(sst) & np.isfinite(thresh)

print(f"Hot days per cell: {hot_mask.sum(axis=0).max()} max, {hot_mask.sum(axis=0).min()} min")

# Now find per-cell MHWs
# For each sea cell:
#   - Find runs of >= 5 consecutive hot days
#   - Join runs separated by 1 or 2 non-hot days

# Initialize MHW mask: (n_time, n_lat, n_lon) - 1 if inside a per-cell MHW
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i,j]:
            continue
        hot = hot_mask[:, i, j]
        
        # Find hot runs
        # First, find all consecutive hot runs
        runs = []
        start = None
        for t in range(n_time):
            if hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    runs.append((start, t-1))
                    start = None
        if start is not None:
            runs.append((start, n_time-1))
        
        if not runs:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        # First, identify all runs >= 5 days
        # Then, join runs that are separated by 1-2 non-hot days
        
        # Find all maximal runs (after joining)
        # A merged run is a sequence of hot runs where gaps between them are 1-2 days
        
        merged_runs = []
        current_start = runs[0][0]
        current_end = runs[0][1]
        
        for k in range(1, len(runs)):
            gap = runs[k][0] - current_end - 1
            if gap <= 2:
                # Join
                current_end = runs[k][1]
            else:
                merged_runs.append((current_start, current_end))
                current_start = runs[k][0]
                current_end = runs[k][1]
        merged_runs.append((current_start, current_end))
        
        # Keep only merged runs with length >= 5
        for (s, e) in merged_runs:
            if e - s + 1 >= 5:
                mhw_mask[s:e+1, i, j] = 1

print(f"MHW mask sum: {mhw_mask.sum()}")

# Save intermediate
np.save('/tmp/hot_mask.npy', hot_mask)
np.save('/tmp/mhw_mask.npy', mhw_mask)
print("Saved")
