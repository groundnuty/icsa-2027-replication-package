
import numpy as np
import pickle
from datetime import date

# Load data
target_data = np.load('/tmp/target_data.npy')
threshold = np.load('/tmp/threshold.npy')
climatology = np.load('/tmp/climatology.npy')

with open('/tmp/dates.pkl', 'rb') as f:
    dates = pickle.load(f)
target_dates = dates['target_dates']

# DOY mapping
def doy_from_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month - 1] + d.day

# Get DOY for each target date
target_doys = [doy_from_date(d) for d in target_dates]
print(f"Target DOYs: {target_doys}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}, count={len(target_dates)}")

# Sea cells
sea_mask = np.all(np.isfinite(target_data), axis=0)
print(f"Sea cells: {sea_mask.sum()}")

# For each sea cell, find hot days
# hot[cell, day] = 1 if SST >= threshold, 0 otherwise
n_days = len(target_dates)
n_lat, n_lon = 60, 60

hot = np.zeros((n_lat, n_lon, n_days), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        for t in range(n_days):
            sst = target_data[t, i, j]
            if np.isnan(sst):
                hot[i, j, t] = False
            else:
                doy = target_doys[t]
                thr = threshold[i, j, doy - 1]
                hot[i, j, t] = (sst >= thr)

print(f"Hot cells-days: {hot.sum()}")
print(f"Total sea cell-days: {sea_mask.sum() * n_days}")

# Now find per-cell MHWs
# A run of at least 5 consecutive hot days
# Per-cell MHWs separated by 1 or 2 non-hot days are joined

# For each cell, identify MHW periods (as boolean mask over target days)
cell_mhw = np.zeros((n_lat, n_lon, n_days), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        h = hot[i, j, :]
        
        # Find runs of hot days
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_days):
            if h[t] and not in_run:
                in_run = True
                run_start = t
            elif not h[t] and in_run:
                in_run = False
                run_end = t - 1
                if run_end - run_start + 1 >= 5:
                    runs.append((run_start, run_end))
        if in_run:
            run_end = n_days - 1
            if run_end - run_start + 1 >= 5:
                runs.append((run_start, run_end))
        
        # Join runs separated by 1-2 non-hot days
        if len(runs) > 0:
            joined = [runs[0]]
            for k in range(1, len(runs)):
                prev_end = joined[-1][1]
                curr_start = runs[k][0]
                gap = curr_start - prev_end - 1
                if gap <= 2:
                    # Join
                    joined[-1] = (joined[-1][0], runs[k][1])
                else:
                    joined.append(runs[k])
            
            # Mark MHW days
            for start, end in joined:
                cell_mhw[i, j, start:end+1] = True

print(f"Cells in MHW: {(cell_mhw.any(axis=2) & sea_mask).sum()}")

# Regional events
# A day is active if at least one sea cell is in a per-cell MHW on that day
active = np.any(cell_mhw, axis=(0, 1))
print(f"Active days: {active.sum()}")

# Find maximal runs of active days
events = []
in_event = False
event_start = 0
for t in range(n_days):
    if active[t] and not in_event:
        in_event = True
        event_start = t
    elif not active[t] and in_event:
        in_event = False
        events.append((target_dates[event_start], target_dates[t-1]))
if in_event:
    events.append((target_dates[event_start], target_dates[n_days-1]))

print(f"Regional events: {len(events)}")
for onset, end in events:
    print(f"  {onset} to {end}")

# Save intermediate results
np.save('/tmp/hot.npy', hot)
np.save('/tmp/cell_mhw.npy', cell_mhw)
np.save('/tmp/sea_mask.npy', sea_mask)
print("Saved intermediate results")
