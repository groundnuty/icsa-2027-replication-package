import numpy as np
import json
import os
from datetime import datetime, timedelta
import h5py

# Create output directory
os.makedirs('output', exist_ok=True)

# Load all intermediate data
target_data = np.load('/work/target_data.npy').astype(np.float64)
threshold_smooth = np.load('/work/threshold_smooth.npy')

# Read coordinate values from the original file
f = h5py.File('/work/sst_s2.nc', 'r')
region_lats = f['latitude'][217:277].astype(np.float64)  # 60 values
region_lons = f['longitude'][421:481].astype(np.float64)  # 60 values

# Get time values for target period and convert to datetime64
time_raw = f['time'][9282:9374]
epoch = datetime(1981, 1, 1)
target_dates = [epoch + timedelta(seconds=int(t)) for t in time_raw]
time_vals = np.array([np.datetime64(dt.isoformat()) for dt in target_dates])
print("Time values:", time_vals[0], "to", time_vals[-1])

# Day-of-year mapping
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

target_doy = np.array([day_of_year(dt.month, dt.day) for dt in target_dates])

# Sea cells
sea_mask = np.all(~np.isnan(target_data), axis=0)
print(f"Sea cells: {np.sum(sea_mask)}")

# Compute hot mask
hot = np.zeros((92, 60, 60), dtype=bool)
for t in range(92):
    doy = target_doy[t]
    hot[t] = (target_data[t] >= threshold_smooth[:, :, doy-1]) & sea_mask

# Detect per-cell MHWs
def detect_cell_mhw(hot_cell):
    n = len(hot_cell)
    runs = []
    in_run = False
    for i in range(n):
        if hot_cell[i]:
            if not in_run:
                run_start = i
                in_run = True
        else:
            if in_run:
                runs.append((run_start, i - 1))
                in_run = False
    if in_run:
        runs.append((run_start, n - 1))
    
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if len(mhws) <= 1:
        joined = mhws
    else:
        joined = [mhws[0]]
        for i in range(1, len(mhws)):
            prev_s, prev_e = joined[-1]
            curr_s, curr_e = mhws[i]
            gap = curr_s - prev_e - 1
            if gap <= 2:
                joined[-1] = (prev_s, curr_e)
            else:
                joined.append((curr_s, curr_e))
    
    mask = np.zeros(n, dtype=bool)
    for s, e in joined:
        mask[s:e+1] = True
    return mask

# Compute per-cell MHW mask for all cells
cell_mhw_mask = np.zeros((92, 60, 60), dtype=bool)
for i in range(60):
    for j in range(60):
        if sea_mask[i, j]:
            cell_mhw_mask[:, i, j] = detect_cell_mhw(hot[:, i, j])

# Save the cell MHW mask
np.save('/work/cell_mhw_mask.npy', cell_mhw_mask)
print(f"Per-cell MHW mask computed. Total MHW cell-days: {np.sum(cell_mhw_mask)}")

# Regional events
active = np.any(cell_mhw_mask, axis=(1, 2))
print("Active days:", np.where(active)[0])

# Find maximal runs of consecutive active days
events = []
in_event = False
for t in range(92):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, 91))

print(f"Regional events: {len(events)}")
event_list = []
for s, e in events:
    onset = target_dates[s].strftime('%Y-%m-%d')
    end = target_dates[e].strftime('%Y-%m-%d')
    print(f"  Event: {onset} to {end}")
    event_list.append({"onset": onset, "end": end})
