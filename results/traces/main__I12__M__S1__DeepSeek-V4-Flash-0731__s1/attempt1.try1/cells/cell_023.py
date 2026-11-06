
import numpy as np

# Load data
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')

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

# Find cells with gaps in hot pattern within an MHW
# These would be cells where per_cell_mhw[t]=1 but hot[t]=0 (gap days)
gap_cells = []
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        for t in range(n_target):
            if per_cell_mhw[t, i, j] and not hot[t, i, j]:
                gap_cells.append((i, j, t))
                break  # just report the first one for each cell

print(f"Cells with gap days in MHW: {len(gap_cells)}")
if gap_cells:
    print("First few:")
    for (i, j, t) in gap_cells[:5]:
        print(f"  Cell ({i},{j}), gap day {t} ({target_dates[t]}): hot={hot[t,i,j]}, in_mhw={per_cell_mhw[t,i,j]}")
        # Show hot pattern around this gap
        start = max(0, t-5)
        end = min(n_target-1, t+5)
        print(f"    Hot pattern days {start}-{end}: {hot[start:end+1, i, j].astype(int)}")
        print(f"    MHW pattern days {start}-{end}: {per_cell_mhw[start:end+1, i, j].astype(int)}")
