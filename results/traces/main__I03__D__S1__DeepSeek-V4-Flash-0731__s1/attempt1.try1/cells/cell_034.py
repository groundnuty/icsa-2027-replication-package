
import numpy as np
import pickle
import datetime as dt

# Load state
sea_cells = np.load('/work/sea_cells.npy')
target_sst = np.load('/work/target_sst.npy')
threshold_smoothed = np.load('/work/threshold_smoothed.npy')
mhw_mask = np.load('/work/mhw_mask.npy')

with open('/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)

def day_of_year(date):
    month = date.month
    day = date.day
    cum_days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_before[month - 1] + day

target_doy = [day_of_year(d) for d in target_dates]
n_target = len(target_dates)

# Find a cell with MHW activity
sea_idx = np.where(sea_cells)
found = False
for k in range(len(sea_idx[0])):
    i, j = sea_idx[0][k], sea_idx[1][k]
    if np.any(mhw_mask[:, i, j] > 0):
        found = True
        print(f"Found MHW cell at ({i},{j})")
        print(f"mhw_mask for this cell: {mhw_mask[:, i, j]}")
        
        # Manual check
        sst_cell = target_sst[:, i, j]
        thr_cell = np.array([threshold_smoothed[doy - 1, i, j] for doy in target_doy])
        
        hot = np.zeros(n_target, dtype=bool)
        for t in range(n_target):
            if np.isfinite(sst_cell[t]) and np.isfinite(thr_cell[t]):
                hot[t] = sst_cell[t] >= thr_cell[t]
        
        print(f"\nHot days: {np.where(hot)[0]}")
        print(f"SST and threshold for hot days:")
        for t in np.where(hot)[0]:
            print(f"  Day {t} ({target_dates[t].date()}): SST={sst_cell[t]}, thr={thr_cell[t]}, hot={hot[t]}")
        
        break

if not found:
    print("No cell with MHW activity found (unexpected)")
