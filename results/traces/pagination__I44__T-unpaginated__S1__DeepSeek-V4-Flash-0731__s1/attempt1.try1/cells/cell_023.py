import numpy as np

sea_cells = np.load('/tmp/work/sea_cells.npy')
threshold_smooth = np.load('/tmp/work/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/work/climatology_smooth.npy')

# Check if all sea cells have finite threshold for all 366 days
sea_idx = np.argwhere(sea_cells)
print(f"Sea cells: {len(sea_idx)}")

# Check finite threshold for sea cells
n_finite_thresh = 0
n_finite_clim = 0
for i, j in sea_idx:
    if np.all(np.isfinite(threshold_smooth[:, i, j])):
        n_finite_thresh += 1
    if np.all(np.isfinite(climatology_smooth[:, i, j])):
        n_finite_clim += 1

print(f"Sea cells with all finite thresholds: {n_finite_thresh}/{len(sea_idx)}")
print(f"Sea cells with all finite climatology: {n_finite_clim}/{len(sea_idx)}")

# Check if any sea cell has NaN threshold on any target day
def month_day_to_doy(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

from datetime import date, timedelta
import pickle
with open('/tmp/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)

for t, d in enumerate(target_dates):
    doy = month_day_to_doy(d.month, d.day)
    for i, j in sea_idx:
        if not np.isfinite(threshold_smooth[doy-1, i, j]):
            print(f"NaN threshold for cell ({i},{j}) on {d} (doy={doy})")
            break
    else:
        continue
    break
else:
    print("All sea cells have finite thresholds on all target days")
