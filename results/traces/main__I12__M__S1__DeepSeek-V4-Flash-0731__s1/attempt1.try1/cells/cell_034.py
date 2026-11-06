
import numpy as np

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Target days of year
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

# Check thresholds for sea cells on all target days
n_seas = sea_cells.sum()
print(f"Sea cells: {n_seas}")

nan_count = 0
for t, doy in enumerate(target_doy):
    thresh = threshold_smooth[doy-1]
    clim = climatology_smooth[doy-1]
    for i in range(60):
        for j in range(60):
            if sea_cells[i, j]:
                if np.isnan(thresh[i, j]) or np.isnan(clim[i, j]):
                    nan_count += 1

print(f"NaN thresholds/climatology for sea cells: {nan_count}")

# Also check raw (pre-smoothing) values
threshold_raw = np.load('/tmp/threshold_raw.npy')
climatology_raw = np.load('/tmp/climatology_raw.npy')

nan_count_raw = 0
for t, doy in enumerate(target_doy):
    thresh = threshold_raw[doy-1]
    clim = climatology_raw[doy-1]
    for i in range(60):
        for j in range(60):
            if sea_cells[i, j]:
                if np.isnan(thresh[i, j]) or np.isnan(clim[i, j]):
                    nan_count_raw += 1

print(f"NaN raw thresholds/climatology for sea cells: {nan_count_raw}")
