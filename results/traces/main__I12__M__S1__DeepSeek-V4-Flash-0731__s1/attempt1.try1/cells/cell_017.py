
import numpy as np
from datetime import date, timedelta

# Load data
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')

n_target, n_lat, n_lon = target_data.shape

# Target dates
target_dates = []
d = date(2009, 6, 1)
while d <= date(2009, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Day of year function
def day_of_year(d):
    month = d.month
    day = d.day
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month]) + day
    if month > 2:
        doy += 1
    return doy

# Get day of year for each target date
target_doy = np.array([day_of_year(d) for d in target_dates])
print("Target day of year:", target_doy)

# For each sea cell, determine hot days
# hot[day, cell_i, cell_j] = 1 if hot
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)

for t in range(n_target):
    doy = target_doy[t] - 1  # 0-indexed
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cells[i, j] and not np.isnan(target_data[t, i, j]):
                hot[t, i, j] = target_data[t, i, j] >= threshold_smooth[doy, i, j]

print(f"Hot day-cell count: {hot.sum()}")
print(f"Hot days per cell (first 10 sea cells):")

# Find per-cell MHWs
# For each sea cell:
#   1. Find runs of >=5 consecutive hot days
#   2. Join runs separated by 1-2 non-hot days

per_cell_mhw = np.zeros((n_target, n_lat, n_lon), dtype=bool)  # True if in a per-cell MHW

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        # Get hot vector for this cell
        h = hot[:, i, j]
        
        # Find runs of hot days
        # First, identify maximal hot runs
        runs = []  # list of (start_idx, end_idx) inclusive
        t = 0
        while t < n_target:
            if h[t]:
                start = t
                while t < n_target and h[t]:
                    t += 1
                runs.append((start, t-1))
            else:
                t += 1
        
        if len(runs) == 0:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        joined = []
        current = runs[0]
        for run in runs[1:]:
            gap = run[0] - current[1] - 1
            if gap <= 2:
                # Join
                current = (current[0], run[1])
            else:
                joined.append(current)
                current = run
        joined.append(current)
        
        # Keep only runs with >= 5 hot days
        for start, end in joined:
            # Count hot days in this joined run
            n_hot = sum(h[start:end+1])
            if n_hot >= 5:
                per_cell_mhw[start:end+1, i, j] = True

print(f"Per-cell MHW cells-day count: {per_cell_mhw.sum()}")

# Check: how many cells have MHWs?
cells_with_mhw = per_cell_mhw.any(axis=0)
print(f"Cells with MHW: {cells_with_mhw.sum()}")

np.save('/tmp/per_cell_mhw.npy', per_cell_mhw)
print("Saved per-cell MHW mask")
