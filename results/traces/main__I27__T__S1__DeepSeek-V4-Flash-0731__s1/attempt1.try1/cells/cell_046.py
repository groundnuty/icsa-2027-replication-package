
import numpy as np
import pandas as pd
import datetime

# Load data
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
clim_smooth = np.load('/tmp/clim_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_data = np.load('/tmp/target_data.npy')
target_times = pd.DatetimeIndex(np.load('/tmp/target_times.npy').astype('datetime64[ns]'))
lat_values = np.load('/tmp/lat_values.npy')
lon_values = np.load('/tmp/lon_values.npy')

def date_to_doy(dt):
    days_in_month_fixed = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month_fixed[:dt.month]) + dt.day

# Map each target date to its day of year index (0-based)
target_doy_idx = np.array([date_to_doy(pd.Timestamp(t)) - 1 for t in target_times])
print("Target doy indices:", target_doy_idx)
print("Target dates:", [str(t.date()) for t in target_times])

# For each sea cell, determine hot days
# hot[i, lat, lon] = 1 if target_data[i, lat, lon] >= threshold_smooth[lat, lon, target_doy_idx[i]]
n_time = len(target_times)
n_lat, n_lon = sea_mask.shape

# Create threshold array for each time step
threshold_for_target = np.zeros((n_time, n_lat, n_lon), dtype=np.float64)
for i in range(n_time):
    threshold_for_target[i] = threshold_smooth[:, :, target_doy_idx[i]]

# Hot days
hot = target_data >= threshold_for_target  # (n_time, n_lat, n_lon) bool
# Only sea cells can be hot
hot = hot & sea_mask[np.newaxis, :, :]

print(f"Hot days: {hot.sum()} out of {n_time * sea_mask.sum()}")
print(f"Hot fraction: {hot.sum() / (n_time * sea_mask.sum()):.4f}")

# For each sea cell, find per-cell MHWs
# A per-cell MHW is a run of >= 5 consecutive hot days
# Join MHWs separated by 1-2 non-hot days

# mhw[i, lat, lon] = 1 if cell is inside a per-cell MHW on day i
mhw = np.zeros_like(hot, dtype=bool)

# Process each sea cell
for lat_i, lon_i in np.argwhere(sea_mask):
    hot_series = hot[:, lat_i, lon_i]
    
    # Find runs of consecutive hot days
    # First, identify all hot runs (regardless of length)
    runs = []
    in_run = False
    start = 0
    for i in range(n_time):
        if hot_series[i] and not in_run:
            start = i
            in_run = True
        elif not hot_series[i] and in_run:
            runs.append((start, i - 1))
            in_run = False
    if in_run:
        runs.append((start, n_time - 1))
    
    # Filter to runs of >= 5 days
    long_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    # Now join runs separated by 1-2 non-hot days
    if long_runs:
        joined_runs = [long_runs[0]]
        for run in long_runs[1:]:
            prev_s, prev_e = joined_runs[-1]
            gap = run[0] - prev_e - 1
            if 1 <= gap <= 2:
                # Join
                joined_runs[-1] = (prev_s, run[1])
            else:
                joined_runs.append(run)
        
        # Mark MHW days
        for s, e in joined_runs:
            mhw[s:e+1, lat_i, lon_i] = True

print(f"MHW days: {mhw.sum()}")

# Save
np.save('/tmp/mhw.npy', mhw)
np.save('/tmp/hot.npy', hot)
print("MHW data saved")

# Now find regional events
# A day is active if at least one sea cell is inside a per-cell MHW
active = np.any(mhw, axis=(1, 2))  # (n_time,)
print("Active days:", active.sum())

# Find maximal runs of consecutive active days
events = []
in_event = False
start = 0
for i in range(n_time):
    if active[i] and not in_event:
        start = i
        in_event = True
    elif not active[i] and in_event:
        events.append((start, i - 1))
        in_event = False
if in_event:
    events.append((start, n_time - 1))

print("Regional events:")
for s, e in events:
    print(f"  {target_times[s].date()} to {target_times[e].date()}, duration={e-s+1} days")
