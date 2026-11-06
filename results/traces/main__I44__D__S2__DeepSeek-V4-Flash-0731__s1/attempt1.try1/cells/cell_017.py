
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

# Check hot day counts for all cells
hot_all = np.zeros(target_data.shape, dtype=bool)
for t in range(len(target_dates)):
    d = target_doys[t] - 1
    hot_all[t] = target_data[t] >= thresholds_smooth[:, :, d]

# For each sea cell, check runs of hot days
print("Checking hot runs for sea cells:")
for lat_i in range(60):
    for lon_i in range(60):
        if not sea_cells[lat_i, lon_i]:
            continue
        
        hot_cell = hot_all[:, lat_i, lon_i]
        
        # Find runs
        runs = []
        in_run = False
        run_start = 0
        for t in range(len(target_dates)):
            if hot_cell[t] and not in_run:
                in_run = True
                run_start = t
            elif not hot_cell[t] and in_run:
                in_run = False
                runs.append((run_start, t-1, t-run_start))
        if in_run:
            runs.append((run_start, len(target_dates)-1, len(target_dates)-run_start))
        
        if runs:
            long_runs = [r for r in runs if r[2] >= 5]
            if long_runs:
                for r in long_runs:
                    print(f"  Cell ({lat_i},{lon_i}): run days {r[0]}-{r[1]} ({r[2]} days), dates {target_dates[r[0]].date()} to {target_dates[r[1]].date()}")

print("\nDone checking hot runs")
