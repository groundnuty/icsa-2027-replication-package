
import numpy as np
import pandas as pd

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')
sea_cells = np.load('/work/sea_cells.npy')
target_data = np.load('/work/target_data.npy')
thresholds_smooth = np.load('/work/thresholds_smooth.npy')

target_dates = pd.date_range('2004-06-01', '2004-08-31', freq='D')

def doy(month, day):
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

target_doys = np.array([doy(dt.month, dt.day) for dt in target_dates])

# Compute hot days
hot_all = np.zeros(target_data.shape, dtype=bool)
for t in range(len(target_dates)):
    d = target_doys[t] - 1
    hot_all[t] = target_data[t] >= thresholds_smooth[:, :, d]

# Check for cells where runs need to be joined (separated by 1-2 non-hot days)
# First find all runs of >= 5 hot days for each cell
join_cases = []
for lat_i in range(60):
    for lon_i in range(60):
        if not sea_cells[lat_i, lon_i]:
            continue
        
        hot_cell = hot_all[:, lat_i, lon_i]
        
        # Find all hot runs
        runs = []
        in_run = False
        run_start = 0
        for t in range(len(target_dates)):
            if hot_cell[t] and not in_run:
                in_run = True
                run_start = t
            elif not hot_cell[t] and in_run:
                in_run = False
                runs.append((run_start, t-1))
        if in_run:
            runs.append((run_start, len(target_dates)-1))
        
        # Filter >= 5 days
        long_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Check if any long runs are separated by 1-2 days
        if len(long_runs) > 1:
            for i in range(len(long_runs) - 1):
                gap = long_runs[i+1][0] - long_runs[i][1] - 1
                if gap <= 2:
                    join_cases.append((lat_i, lon_i, long_runs[i], long_runs[i+1], gap))

print(f"Join cases: {len(join_cases)}")
for case in join_cases[:10]:
    lat_i, lon_i, run1, run2, gap = case
    print(f"  Cell ({lat_i},{lon_i}): run1={run1} ({target_dates[run1[0]].date()} to {target_dates[run1[1]].date()}), run2={run2} ({target_dates[run2[0]].date()} to {target_dates[run2[1]].date()}), gap={gap}")

# Also check: how many runs of >= 5 exist per cell
max_runs = 0
for lat_i in range(60):
    for lon_i in range(60):
        if not sea_cells[lat_i, lon_i]:
            continue
        hot_cell = hot_all[:, lat_i, lon_i]
        runs = []
        in_run = False
        run_start = 0
        for t in range(len(target_dates)):
            if hot_cell[t] and not in_run:
                in_run = True
                run_start = t
            elif not hot_cell[t] and in_run:
                in_run = False
                runs.append((run_start, t-1))
        if in_run:
            runs.append((run_start, len(target_dates)-1))
        
        long_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        if len(long_runs) > max_runs:
            max_runs = len(long_runs)
print(f"\nMax number of long runs per cell: {max_runs}")
