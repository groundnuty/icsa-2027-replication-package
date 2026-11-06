import numpy as np

# Load data
target_data = np.load('/work/target_data.npy').astype(np.float64)
threshold_smooth = np.load('/work/threshold_smooth.npy')

sea_mask = np.all(~np.isnan(target_data), axis=0)
sea_cells = np.argwhere(sea_mask)
print(f"Sea cells: {len(sea_cells)}")

# Day-of-year for target dates
from datetime import datetime, timedelta

def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

target_dates = []
d = datetime(2007, 6, 1)
while d <= datetime(2007, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

target_doy = np.array([day_of_year(dt.month, dt.day) for dt in target_dates])

# Compute hot mask for all sea cells
hot = np.zeros((92, 60, 60), dtype=bool)
for t in range(92):
    doy = target_doy[t]
    hot[t] = (target_data[t] >= threshold_smooth[:, :, doy-1]) & sea_mask

# Check how many hot cells on each day
for t in range(92):
    n_hot = np.sum(hot[t])
    if n_hot > 0:
        print(f"Day {t} ({target_dates[t].date()}): {n_hot} hot cells")
