import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd

# Load data
target_ds = xr.open_dataset('/tmp/target_data.nc')
target_sst = target_ds['analysed_sst'].values.astype(np.float64)  # (92, 60, 60)
target_time = target_ds['time'].values
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

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

# Compute hot days for each cell
# hot[c, t] = 1 if cell c is hot on day t
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    doy = target_doy[t]
    thresh = threshold_smooth[doy]  # (60, 60)
    hot[t] = target_sst[t] >= thresh

# Apply sea mask (land cells are not hot)
hot &= sea_mask[np.newaxis, :, :]

# Find per-cell MHWs
# For each cell, find runs of >= 5 consecutive hot days
# Join runs separated by 1-2 non-hot days

# mhw[c, t] = 1 if cell c is inside a per-cell MHW on day t
mhw = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        
        h = hot[:, i, j]  # (n_time,)
        
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
        
        if not runs:
            continue
        
        # Filter runs of length >= 5
        long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        if not long_runs:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined = []
        current = long_runs[0]
        for r in long_runs[1:]:
            # Check gap between current end and r start
            gap = r[0] - current[1] - 1
            if 1 <= gap <= 2:
                # Join
                current = (current[0], r[1])
            else:
                joined.append(current)
                current = r
        joined.append(current)
        
        # Mark cells in MHW
        for start, end in joined:
            mhw[start:end+1, i, j] = True

# Check number of per-cell MHWs
print("Per-cell MHW days (sum):", mhw.sum())
print("Cells with MHWs:", np.any(mhw, axis=0).sum())

# Regional events
# A day is active if at least one sea cell is inside a per-cell MHW
active = np.any(mhw, axis=(1, 2))  # (n_time,)
print("Active days:", active.sum())

# Find maximal runs of consecutive active days
events = []
start = None
for t in range(n_time):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t-1))
            start = None
if start is not None:
    events.append((start, n_time-1))

print("Regional events:", len(events))
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]} ({e-s+1} days)")

# Save mhw mask
np.save('/tmp/mhw_mask.npy', mhw)
