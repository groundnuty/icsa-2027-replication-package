import numpy as np
from datetime import date, timedelta
import pickle

# Reload data
target_sst = np.load('/tmp/work/target_sst.npy')
with open('/tmp/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
sea_cells = np.load('/tmp/work/sea_cells.npy')
threshold_smooth = np.load('/tmp/work/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/work/climatology_smooth.npy')
per_cell_mhw = np.load('/tmp/work/per_cell_mhw.npy')

n_target, n_lat, n_lon = target_sst.shape

def month_day_to_doy(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Check cell (38, 2)
i, j = 38, 2
print(f"Cell ({i},{j}): sea={sea_cells[i,j]}")
print(f"  SST values and hot status:")
for t in range(n_target):
    d = target_dates[t]
    doy = month_day_to_doy(d.month, d.day)
    sst = target_sst[t, i, j]
    thresh = threshold_smooth[doy-1, i, j]
    is_hot = sst >= thresh
    in_mhw = per_cell_mhw[t, i, j]
    if is_hot or in_mhw:
        print(f"    {d}: sst={sst:.3f}, thresh={thresh:.3f}, hot={is_hot}, mhw={in_mhw}")

print(f"\nMHW mask for cell ({i},{j}):")
for t in range(n_target):
    if per_cell_mhw[t, i, j]:
        print(f"  {target_dates[t]}")
