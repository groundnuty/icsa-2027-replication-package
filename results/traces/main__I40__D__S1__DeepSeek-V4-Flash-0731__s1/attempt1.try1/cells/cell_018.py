
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load data
target_sst = np.load('/work/target_sst.npy')
targ_times = np.load('/work/targ_times.npy')
thresholds = np.load('/work/thresholds.npy')

targ_dates = pd.DatetimeIndex(targ_times)
n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
n_targ = len(targ_dates)

# Day of year mapping
def date_to_doy(dt):
    """Map a datetime to day of year 1-366 as specified."""
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

targ_doy = np.array([date_to_doy(d) for d in targ_dates])
print(f"Target doys: {targ_doy}")

# Sea cells
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        if np.all(np.isfinite(target_sst[:, i, j])):
            sea_cells[i, j] = True

# Determine hot days per cell
# hot[day, lat, lon] = 1 if SST >= threshold for that doy
hot = np.zeros((n_targ, n_lat, n_lon), dtype=bool)

for t in range(n_targ):
    d = targ_doy[t]
    thr = thresholds[d-1, :, :]  # threshold for this doy, per cell
    # For sea cells, check if SST >= threshold
    sst_t = target_sst[t, :, :]
    hot[t] = (sst_t >= thr) & sea_cells & np.isfinite(sst_t) & np.isfinite(thr)

print(f"Hot days count: {hot.sum()}")
print(f"Hot fraction: {hot.sum() / (n_targ * n_lat * n_lon):.4f}")

# Find per-cell MHWs: runs of >=5 consecutive hot days, join gaps of 1-2 non-hot days
# mhw_mask[t, lat, lon] = 1 if cell is inside a per-cell MHW on day t
mhw_mask = np.zeros((n_targ, n_lat, n_lon), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        hot_series = hot[:, i, j]
        
        # Find hot runs
        runs = []
        t = 0
        while t < n_targ:
            if hot_series[t]:
                start = t
                while t < n_targ and hot_series[t]:
                    t += 1
                end = t - 1
                runs.append((start, end))
            else:
                t += 1
        
        if len(runs) == 0:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        joined = [list(runs[0])]
        for k in range(1, len(runs)):
            gap = runs[k][0] - joined[-1][1] - 1
            if gap <= 2:
                # Join: extend the joined run to include the gap and the new run
                joined[-1][1] = runs[k][1]
            else:
                joined.append(list(runs[k]))
        
        # Check if joined runs are >= 5 days
        for start, end in joined:
            if end - start + 1 >= 5:
                mhw_mask[start:end+1, i, j] = True

print(f"MHW mask sum: {mhw_mask.sum()}")

# Regional events: active if at least one sea cell is in an MHW
active = mhw_mask.any(axis=(1, 2))
print(f"Active days: {active.sum()}")
print(f"Active day indices: {np.where(active)[0]}")

# Find regional events: maximal runs of consecutive active days
events = []
t = 0
while t < n_targ:
    if active[t]:
        start = t
        while t < n_targ and active[t]:
            t += 1
        end = t - 1
        events.append((start, end))
    else:
        t += 1

print(f"\nRegional events:")
for start, end in events:
    print(f"  {targ_dates[start].strftime('%Y-%m-%d')} to {targ_dates[end].strftime('%Y-%m-%d')} ({end - start + 1} days)")
