
import numpy as np

# Load data
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')

from datetime import date, timedelta

def day_of_year(d):
    month = d.month
    day = d.day
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month]) + day
    if month > 2:
        doy += 1
    return doy

target_dates = []
d = date(2009, 6, 1)
while d <= date(2009, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

target_doy = np.array([day_of_year(d) for d in target_dates])

n_target, n_lat, n_lon = target_data.shape

# Recompute hot mask
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for t in range(n_target):
    doy = target_doy[t] - 1
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cells[i, j] and not np.isnan(target_data[t, i, j]):
                hot[t, i, j] = target_data[t, i, j] >= threshold_smooth[doy, i, j]

# Count runs of hot days per cell
max_runs = 0
cells_with_gaps = 0
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        h = hot[:, i, j]
        # Find runs
        runs = []
        t = 0
        while t < n_target:
            if h[t]:
                start = t
                while t < n_target and h[t]:
                    t += 1
                runs.append((start, t-1, t-start))  # (start, end, length)
            else:
                t += 1
        if len(runs) > max_runs:
            max_runs = len(runs)
        # Check for gaps between runs
        if len(runs) >= 2:
            for k in range(len(runs)-1):
                gap = runs[k+1][0] - runs[k][1] - 1
                if gap <= 2:
                    cells_with_gaps += 1
                    break

print(f"Max number of hot runs per cell: {max_runs}")
print(f"Cells with runs separated by <=2 days: {cells_with_gaps}")
