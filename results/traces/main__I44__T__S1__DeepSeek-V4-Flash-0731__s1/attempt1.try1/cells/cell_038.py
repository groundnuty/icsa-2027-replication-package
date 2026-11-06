import numpy as np
import xarray as xr
import pandas as pd

# Load data
target_ds = xr.open_dataset('/tmp/target_data.nc')
target_sst = target_ds['analysed_sst'].values.astype(np.float64)
target_time = target_ds['time'].values
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

def day_of_year(date):
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    if not is_leap and date.month >= 3:
        doy += 1
    return doy

target_doy = [day_of_year(d) for d in target_dates]
n_time = len(target_dates)
n_lat, n_lon = 60, 60

# Compute hot days
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    hot[t] = target_sst[t] >= threshold_smooth[doy]
hot &= sea_mask[np.newaxis, :, :]

# Find per-cell MHWs and count cells where runs were joined
joined_cells = 0
for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        h = hot[:, i, j]
        
        # Find hot runs
        runs = []
        start = None
        for t in range(n_time):
            if h[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    runs.append((start, t-1))
                    start = None
        if start is not None:
            runs.append((start, n_time-1))
        
        # Keep runs of length >= 5
        long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Check if any long runs are joined
        if len(long_runs) >= 2:
            for k in range(len(long_runs)-1):
                gap = long_runs[k+1][0] - long_runs[k][1] - 1
                if 1 <= gap <= 2:
                    joined_cells += 1
                    break

print(f"Cells where runs were joined: {joined_cells}")
