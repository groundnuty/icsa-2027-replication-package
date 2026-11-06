
import numpy as np

# Load data
tgt_data = np.load('/tmp/tgt_data.npy')  # (92, 60, 60)
tgt_times = np.load('/tmp/tgt_times.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')  # (366, 60, 60)
clim_smooth = np.load('/tmp/clim_smooth.npy')

import pandas as pd

# Compute day-of-year for each target date
def day_of_year(month, day):
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and day == 29:
        return 60
    doy = sum(days_in_month[:month-1]) + day
    if month > 2:
        doy += 1
    return doy

tgt_doy = np.array([day_of_year(pd.Timestamp(t).to_pydatetime().month, 
                                pd.Timestamp(t).to_pydatetime().day) for t in tgt_times])

print("Target DOYs:", tgt_doy)
print("Target times:", tgt_times[:3], "...", tgt_times[-3:])

# Identify sea cells: finite SST on every target day
sea_mask = np.all(np.isfinite(tgt_data), axis=0)  # (60, 60)
print("Sea cells:", sea_mask.sum(), "out of", sea_mask.size)
print("NaN in target data by cell:", np.isnan(tgt_data).sum(axis=0).max() if sea_mask.sum() > 0 else 0)

# Check which cells are sea cells
sea_indices = np.where(sea_mask)
print("Sea cell coordinates (lat, lon):")
for i in range(min(5, len(sea_indices[0]))):
    lat_i, lon_i = sea_indices[0][i], sea_indices[1][i]
    print(f"  ({lat_i}, {lon_i})")
