
import numpy as np
from datetime import date, timedelta

# Load data
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')

n_target, n_lat, n_lon = target_data.shape

# Target dates
target_dates = []
d = date(2009, 6, 1)
while d <= date(2009, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

def day_of_year(d):
    month = d.month
    day = d.day
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month]) + day
    if month > 2:
        doy += 1
    return doy

target_doy = np.array([day_of_year(d) for d in target_dates])

# Compute hot mask
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for t in range(n_target):
    doy = target_doy[t] - 1
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cells[i, j] and not np.isnan(target_data[t, i, j]):
                hot[t, i, j] = target_data[t, i, j] >= threshold_smooth[doy, i, j]

# Per-cell MHW detection
# Step 1: Find runs of >= 5 consecutive hot days (candidate MHWs)
# Step 2: Join candidate MHWs separated by 1-2 non-hot days

per_cell_mhw = np.zeros((n_target, n_lat, n_lon), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        h = hot[:, i, j]
        
        # Step 1: Find runs of >= 5 consecutive hot days
        runs = []
        t = 0
        while t < n_target:
            if h[t]:
                start = t
                while t < n_target and h[t]:
                    t += 1
                length = t - start
                if length >= 5:
                    runs.append([start, t-1])  # [start, end] inclusive
            else:
                t += 1
        
        if len(runs) == 0:
            continue
        
        # Step 2: Join runs separated by 1 or 2 non-hot days
        joined = []
        current = runs[0]
        for run in runs[1:]:
            gap = run[0] - current[1] - 1
            if gap <= 2:
                current = [current[0], run[1]]
            else:
                joined.append(current)
                current = run
        joined.append(current)
        
        # Mark all days in joined MHWs
        for start, end in joined:
            per_cell_mhw[start:end+1, i, j] = True

print(f"Per-cell MHW cells-day count: {per_cell_mhw.sum()}")
cells_with_mhw = per_cell_mhw.any(axis=0)
print(f"Cells with MHW: {cells_with_mhw.sum()}")

# Let's check one specific cell in detail
# Find a sea cell
sea_idx = np.argwhere(sea_cells)
print("\nFirst sea cell at (i,j):", sea_idx[0])
i0, j0 = sea_idx[0]

print(f"\nCell ({i0},{j0}):")
print(f"  Hot vector: {hot[:, i0, j0].astype(int)}")

np.save('/tmp/per_cell_mhw.npy', per_cell_mhw)
print("Saved per-cell MHW mask")
