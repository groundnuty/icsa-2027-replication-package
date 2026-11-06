
import numpy as np
from datetime import date, timedelta

# Load data
target_data = np.load('/tmp/target_data.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')

n_target, n_lat, n_lon = target_data.shape

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

# Compute hot mask
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for t in range(n_target):
    doy = target_doy[t] - 1
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_cells[i, j] and not np.isnan(target_data[t, i, j]):
                hot[t, i, j] = target_data[t, i, j] >= threshold_smooth[doy, i, j]

# Find cells that are in MHW on day 23
cells_in_mhw_23 = np.argwhere(per_cell_mhw[23])
print("Cells in MHW on day 23 (indices):", cells_in_mhw_23[:10])

for (i, j) in cells_in_mhw_23[:5]:
    print(f"\nCell ({i},{j}):")
    print(f"  Hot days: {np.where(hot[:, i, j])[0]}")
    print(f"  In MHW: {np.where(per_cell_mhw[:, i, j])[0]}")
    # Check SST on hot days
    for t in np.where(hot[:, i, j])[0][:10]:
        doy = target_doy[t] - 1
        print(f"    Day {t} ({target_dates[t]}): SST={target_data[t, i, j]:.2f}, threshold={threshold_smooth[doy, i, j]:.2f}")
