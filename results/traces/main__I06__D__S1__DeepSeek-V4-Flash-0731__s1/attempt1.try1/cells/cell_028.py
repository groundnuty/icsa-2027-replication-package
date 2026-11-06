
import numpy as np
import datetime
import pandas as pd

# Load data
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
target_time_idx = np.load('/work/target_time_idx.npy')
thresholds_smooth = np.load('/work/thresholds_smooth.npy')  # (366, 60, 60)
climatologies_smooth = np.load('/work/climatologies_smooth.npy')

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values
target_dates = time[target_time_idx]
target_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in target_dates]

print(f"Target dates: {target_dates_list[0]} to {target_dates_list[-1]}")
print(f"Number of target days: {len(target_dates_list)}")

# Compute day of year for each target date
def doy_from_date(date):
    m = date.month
    d = date.day
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    elif m == 3:
        return 60 + d
    elif m == 4:
        return 91 + d
    elif m == 5:
        return 121 + d
    elif m == 6:
        return 152 + d
    elif m == 7:
        return 182 + d
    elif m == 8:
        return 213 + d
    elif m == 9:
        return 244 + d
    elif m == 10:
        return 274 + d
    elif m == 11:
        return 305 + d
    elif m == 12:
        return 335 + d
    return -1

target_doy = [doy_from_date(d) for d in target_dates_list]
print(f"Target days of year: {target_doy}")

# Sea cells: finite SST on every target day
sea_cells = ~np.isnan(target_sst).any(axis=0)  # (60, 60)
print(f"\nSea cells: {sea_cells.sum()}")

# For each sea cell and target day, check if hot (SST >= threshold)
# target_sst: (92, 60, 60) - convert to float64
target_sst64 = target_sst.astype(np.float64)

# Get thresholds for target days
# thresholds_smooth[doy-1] is the threshold for day-of-year doy
target_thresholds = np.zeros((92, 60, 60), dtype=np.float64)
for t, doy in enumerate(target_doy):
    target_thresholds[t] = thresholds_smooth[doy-1]

# Hot: SST >= threshold
hot = target_sst64 >= target_thresholds  # (92, 60, 60)

# Check hot counts
print(f"Hot cells per day: {hot.sum(axis=(1,2))}")
print(f"Total hot cell-days: {hot.sum()}")

# Now find per-cell MHWs
# For each sea cell, find runs of >= 5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

n_target = 92
n_lat, n_lon = 60, 60

# Per-cell MHW mask
mhw_mask = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        hot_series = hot[:, i, j].astype(int)
        
        # Find runs of consecutive hot days
        runs = []  # list of (start, end) inclusive
        
        start = None
        for t in range(n_target):
            if hot_series[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    runs.append((start, t-1))
                    start = None
        if start is not None:
            runs.append((start, n_target-1))
        
        # Filter runs with >= 5 days
        mhw_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        # Join runs separated by 1-2 non-hot days
        if mhw_runs:
            joined = [mhw_runs[0]]
            for s, e in mhw_runs[1:]:
                last_s, last_e = joined[-1]
                gap = s - last_e - 1
                if gap <= 2:
                    # Join
                    joined[-1] = (last_s, e)
                else:
                    joined.append((s, e))
            
            # Mark joined runs in mhw_mask
            for s, e in joined:
                mhw_mask[s:e+1, i, j] = 1

print(f"\nMHW cell-days: {mhw_mask.sum()}")

# Regional events
# A day is active if at least one sea cell is in a per-cell MHW
active = mhw_mask.any(axis=(1, 2))  # (92,)

print(f"Active days: {active.sum()}")

# Find maximal runs of active days
events = []
start = None
for t in range(n_target):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t-1))
            start = None
if start is not None:
    events.append((start, n_target-1))

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates_list[s]} to {target_dates_list[e]} ({e-s+1} days)")
