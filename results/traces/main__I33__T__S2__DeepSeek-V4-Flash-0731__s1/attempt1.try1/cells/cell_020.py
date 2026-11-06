
import numpy as np
import xarray as xr
from datetime import date, timedelta
import pandas as pd

# Load saved data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')
thresholds_smooth = np.load('thresholds_smooth.npy')
climatology_smooth = np.load('climatology_smooth.npy')

# Target data
target_sst = target_data.analysed_sst.values  # shape (92, 60, 60)
target_time = target_data.time.values
n_days, n_lat, n_lon = target_sst.shape
print("Target SST shape:", target_sst.shape)

# Day of year mapping
cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

# Compute day of year for each target day
target_dates = [pd.Timestamp(t).date() for t in target_time.astype('datetime64[D]')]
target_doys = [date_to_doy(d.year, d.month, d.day) for d in target_dates]
print("Target DOYs:", target_doys[:10], "...", target_doys[-5:])

# Identify sea cells (finite SST on all target days)
sea_mask = np.all(~np.isnan(target_sst), axis=0)  # shape (60, 60)
print("Number of sea cells:", np.sum(sea_mask))

# For each cell, check hot days
# Threshold for each target day and cell
threshold_for_target = np.array([thresholds_smooth[doy] for doy in target_doys])  # shape (92, 60, 60)
print("Threshold array shape:", threshold_for_target.shape)

# Hot days: SST >= threshold
hot = (target_sst >= threshold_for_target) & sea_mask[np.newaxis, :, :]
print("Hot days count:", np.sum(hot))

# Detect per-cell MHWs
# For each cell: find runs of >=5 consecutive hot days, then join runs separated by 1-2 non-hot days

# Initialize MHW mask
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        hot_cell = hot[:, i, j]  # shape (92,)
        
        # Find runs of consecutive hot days
        # First, find hot runs
        runs = []
        in_run = False
        run_start = 0
        for d in range(n_days):
            if hot_cell[d]:
                if not in_run:
                    run_start = d
                    in_run = True
            else:
                if in_run:
                    runs.append((run_start, d - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_days - 1))
        
        # Keep only runs of >= 5 days
        runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Join runs separated by 1 or 2 non-hot days
        if len(runs) > 0:
            joined_runs = [list(runs[0])]
            for k in range(1, len(runs)):
                gap = runs[k][0] - joined_runs[-1][1] - 1
                if gap <= 2:
                    joined_runs[-1][1] = runs[k][1]
                else:
                    joined_runs.append(list(runs[k]))
            
            # Mark MHW days
            for start, end in joined_runs:
                mhw_mask[start:end+1, i, j] = 1

print("MHW mask count:", np.sum(mhw_mask))

# Check some stats
print("MHW mask sum per day:")
day_counts = mhw_mask.sum(axis=(1,2))
for d in range(n_days):
    if day_counts[d] > 0:
        print(f"  Day {d} ({target_dates[d]}): {day_counts[d]} cells")
