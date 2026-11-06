
import numpy as np
from datetime import date

# Load data
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smoothed = np.load('/tmp/threshold_smoothed.npy')

with open('/tmp/target_dates.txt') as f:
    target_dates_str = [line.strip() for line in f]
target_dates = [date.fromisoformat(s) for s in target_dates_str]

def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d.day + sum(month_days[:d.month])

# Verify day of year for target dates
for d in [target_dates[0], target_dates[30], target_dates[-1]]:
    print(f"{d} -> doy {day_of_year(d)}")

# For each target day, compute the day-of-year index
doy_indices = [day_of_year(d) - 1 for d in target_dates]  # 0-based index into threshold array

n_days = len(target_dates)
n_lat, n_lon = target_data.shape[1], target_data.shape[2]

# Determine hot days for each cell
# For each cell and day, check if SST >= threshold[doy]
hot = np.zeros((n_days, n_lat, n_lon), dtype=bool)

for i, doy_idx in enumerate(doy_indices):
    thresh = threshold_smoothed[doy_idx]  # (n_lat, n_lon)
    # Compare SST >= threshold
    hot[i] = target_data[i] >= thresh

# For land cells, set hot = False
hot[:, ~sea_cells] = False

print(f"Hot days count: {hot.sum()}")
print(f"Hot days shape: {hot.shape}")

# Find per-cell MHWs
# A per-cell MHW is a run of at least 5 consecutive hot days
# Per-cell MHWs separated by 1 or 2 non-hot days are joined into one

# For each cell, find MHW intervals
cell_mhw = np.zeros((n_days, n_lat, n_lon), dtype=bool)  # True if cell is inside a per-cell MHW on that day

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        h = hot[:, i, j]
        
        # Find runs of hot days
        runs = []
        start = None
        for t in range(n_days):
            if h[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    runs.append((start, t-1))
                    start = None
        if start is not None:
            runs.append((start, n_days-1))
        
        # Filter to runs of at least 5 days
        long_runs = [(s, e) for s, e in runs if (e - s + 1) >= 5]
        
        if not long_runs:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        joined = []
        current_start, current_end = long_runs[0]
        for s, e in long_runs[1:]:
            if s - current_end <= 3:  # gap of 1 or 2 days
                current_end = e
            else:
                joined.append((current_start, current_end))
                current_start, current_end = s, e
        joined.append((current_start, current_end))
        
        # Mark cell as in MHW during joined intervals
        for s, e in joined:
            cell_mhw[s:e+1, i, j] = True

print(f"Cells in MHW on any day: {(cell_mhw.any(axis=0)).sum()}")
print(f"Total cell-MHW day pairs: {cell_mhw.sum()}")

# Save
np.save('/tmp/cell_mhw.npy', cell_mhw)
print("Saved per-cell MHW data")
