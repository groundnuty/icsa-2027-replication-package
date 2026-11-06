import numpy as np

# Load data
target_data = np.load('/work/target_data.npy').astype(np.float64)
threshold_smooth = np.load('/work/threshold_smooth.npy')
cell_mhw_mask = np.load('/work/cell_mhw_mask.npy')

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
sea_mask = np.all(~np.isnan(target_data), axis=0)

# Compute hot mask
hot = np.zeros((92, 60, 60), dtype=bool)
for t in range(92):
    doy = target_doy[t]
    hot[t] = (target_data[t] >= threshold_smooth[:, :, doy-1]) & sea_mask

# Check for gap days in MHWs (where cell_mhw_mask is True but hot is False)
gap_days = (cell_mhw_mask & ~hot)
print(f"Gap days in MHWs (cell-mhw True but not hot): {np.sum(gap_days)}")

# Find which cells have gap days
for i in range(60):
    for j in range(60):
        if np.any(gap_days[:, i, j]):
            gap_day_indices = np.where(gap_days[:, i, j])[0]
            print(f"Cell ({i},{j}): gap days at indices {gap_day_indices} = dates {[target_dates[k].date() for k in gap_day_indices]}")

# Also verify no gap days at all
if np.sum(gap_days) == 0:
    print("\nNo gap days found - no joined MHWs in the actual data")
