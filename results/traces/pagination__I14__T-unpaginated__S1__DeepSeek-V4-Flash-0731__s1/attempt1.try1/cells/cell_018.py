
import numpy as np
from datetime import date, timedelta

# Load all needed data
target_sst = np.load('target_sst.npy')  # (92, 60, 60)
sea_mask = np.load('sea_mask.npy')
threshold_smooth = np.load('threshold_smooth.npy')  # (366, 60, 60)
climatology_smooth = np.load('climatology_smooth.npy')  # (366, 60, 60)

# Target dates
target_dates = []
d = date(2015, 6, 1)
while d <= date(2015, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)
n_target = len(target_dates)

# Function to compute day-of-year
def day_of_year_fixed(y, m, d):
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    else:
        days_before_month = {3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
        return days_before_month[m] + d

# Compute day-of-year for each target date
target_doy = np.array([day_of_year_fixed(d.year, d.month, d.day) for d in target_dates])
print(f"Target day-of-year: {target_doy}")

# For each sea cell and target day, check if hot (SST >= threshold)
# threshold_smooth is indexed [doy-1, lat, lon]
hot = np.zeros((n_target, 60, 60), dtype=bool)

sea_cells = np.argwhere(sea_mask)
for ci, (lat_i, lon_i) in enumerate(sea_cells):
    for t_idx in range(n_target):
        doy = target_doy[t_idx]
        sst_val = target_sst[t_idx, lat_i, lon_i]
        thresh_val = threshold_smooth[doy-1, lat_i, lon_i]
        if np.isfinite(sst_val) and np.isfinite(thresh_val) and sst_val >= thresh_val:
            hot[t_idx, lat_i, lon_i] = True

print(f"Hot days count: {hot.sum()}")
print(f"Total cell-days: {hot.size}")

# Now find per-cell MHWs: runs of >=5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

# For each sea cell, find MHW periods
per_cell_mhw = np.zeros((n_target, 60, 60), dtype=bool)  # True if cell is in a per-cell MHW

for ci, (lat_i, lon_i) in enumerate(sea_cells):
    hot_series = hot[:, lat_i, lon_i]  # (92,) boolean
    
    # Find runs of consecutive hot days
    runs = []
    i = 0
    while i < n_target:
        if hot_series[i]:
            start = i
            while i < n_target and hot_series[i]:
                i += 1
            runs.append((start, i-1))  # inclusive
        else:
            i += 1
    
    # Filter to runs of at least 5 days
    long_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    # Join runs separated by 1-2 non-hot days
    if long_runs:
        joined_runs = [long_runs[0]]
        for run in long_runs[1:]:
            last_s, last_e = joined_runs[-1]
            gap = run[0] - last_e - 1
            if gap <= 2:  # 1 or 2 non-hot days
                # Join: extend last run to include the gap and this run
                joined_runs[-1] = (last_s, run[1])
            else:
                joined_runs.append(run)
        
        # Mark days in joined runs as MHW days for this cell
        for s, e in joined_runs:
            per_cell_mhw[s:e+1, lat_i, lon_i] = True

print(f"Per-cell MHW days count: {per_cell_mhw.sum()}")

np.save('per_cell_mhw.npy', per_cell_mhw)
print("Per-cell MHWs computed")
