
import numpy as np
import xarray as xr
import pandas as pd
from datetime import datetime

# Load intermediate results
threshold_smooth = np.load('threshold_smooth.npy')
sea_cells = np.load('sea_cells.npy')

# Load target data
target_data = xr.open_dataset('target_data.nc')
target_sst = target_data.analysed_sst.values
target_time = target_data.time.values

# Day of year for target dates
def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month] + day

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = [day_of_year(dt) for dt in target_dates]
n_time = len(target_time)
n_lat = target_sst.shape[1]
n_lon = target_sst.shape[2]

# Convert SST to float64
target_sst_f64 = target_sst.astype(np.float64)

# Determine hot days for each cell
# hot[day, lat, lon] = True if SST >= threshold for that day-of-year
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    doy = target_doy[t]
    doy_idx = doy - 1  # 0-indexed
    for la in range(n_lat):
        for lo in range(n_lon):
            if sea_cells[la, lo]:
                sst_val = target_sst_f64[t, la, lo]
                if np.isfinite(sst_val):
                    thr = threshold_smooth[doy_idx, la, lo]
                    if sst_val >= thr:
                        hot[t, la, lo] = True

print(f"Total hot day-cell entries: {np.sum(hot)}")
print(f"Hot days per time step (sum over cells):")
for t in range(n_time):
    count = np.sum(hot[t, :, :])
    if count > 0:
        print(f"  {target_dates[t].strftime('%Y-%m-%d')}: {count} hot cells")
