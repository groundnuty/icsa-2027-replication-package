
import numpy as np
from datetime import date

# Reload
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smoothed = np.load('/tmp/threshold_smoothed.npy')
cell_mhw = np.load('/tmp/cell_mhw.npy')

with open('/tmp/target_dates.txt') as f:
    target_dates_str = [line.strip() for line in f]
target_dates = [date.fromisoformat(s) for s in target_dates_str]

def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d.day + sum(month_days[:d.month])

# Trace cell (30, 30)
i, j = 30, 30
print(f"Cell ({i},{j}):")
print(f"Sea cell: {sea_cells[i,j]}")

# Get threshold for each target day
doy_indices = [day_of_year(d)-1 for d in target_dates]
thresh = [threshold_smoothed[doy_idx, i, j] for doy_idx in doy_indices]
sst = target_data[:, i, j]

print(f"\nDay-by-day:")
for t in range(len(target_dates)):
    d = target_dates[t]
    doy = day_of_year(d)
    is_hot = sst[t] >= thresh[t]
    in_mhw = cell_mhw[t, i, j]
    marker_hot = "HOT" if is_hot else "   "
    marker_mhw = "MHW" if in_mhw else "   "
    print(f"  {d.isoformat()} doy={doy:3d} sst={sst[t]:8.3f} thresh={thresh[t]:8.3f} {marker_hot} {marker_mhw}")

# Verify runs
h = sst >= np.array(thresh)
print(f"\nHot days: {np.where(h)[0]}")

# Find runs
runs = []
start = None
for t in range(len(target_dates)):
    if h[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            runs.append((start, t-1))
            start = None
if start is not None:
    runs.append((start, len(target_dates)-1))

print(f"Runs: {runs}")
print(f"Runs >= 5 days: {[(s,e) for s,e in runs if e-s+1 >= 5]}")
