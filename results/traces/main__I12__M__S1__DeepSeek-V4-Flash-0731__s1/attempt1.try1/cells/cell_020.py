
import numpy as np
from datetime import date, timedelta

# Load all data
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')

n_target, n_lat, n_lon = target_data.shape

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

# Verify hot calculation for a few cells
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for t in range(n_target):
    doy = target_doy[t] - 1
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cells[i, j] and not np.isnan(target_data[t, i, j]):
                hot[t, i, j] = target_data[t, i, j] >= threshold_smooth[doy, i, j]

# Check day by day: how many cells are hot each day
for t in range(n_target):
    n_hot = hot[t, sea_cells].sum()
    n_mhw = per_cell_mhw[t, sea_cells].sum()
    print(f"Day {t} ({target_dates[t]}): hot={n_hot}, in_mhw={n_mhw}")
