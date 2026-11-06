import numpy as np
from datetime import date, timedelta
import pickle

# Load all needed data
target_sst = np.load('/tmp/work/target_sst.npy')
with open('/tmp/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
sea_cells = np.load('/tmp/work/sea_cells.npy')
threshold_smooth = np.load('/tmp/work/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/work/climatology_smooth.npy')

n_target, n_lat, n_lon = target_sst.shape
print(f"Target SST: {target_sst.shape}")
print(f"Sea cells: {sea_cells.sum()}")

# Day-of-year function
def month_day_to_doy(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

def date_to_doy(d):
    return month_day_to_doy(d.month, d.day)

# Get day-of-year for each target date
target_doy = np.array([date_to_doy(d) for d in target_dates])
print(f"Target day-of-year: {target_doy}")

# For each sea cell, determine hot days
# A day is hot if SST >= threshold for that day of year
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)

for t in range(n_target):
    doy = target_doy[t]
    # threshold for this day: threshold_smooth[doy-1]
    thresh = threshold_smooth[doy-1]  # shape (n_lat, n_lon)
    hot[t] = (target_sst[t] >= thresh) & sea_cells

print(f"Hot days: {hot.sum()} out of {n_target * n_lat * n_lon}")
print(f"Hot days (sea cells only): {hot.sum()}")

# Find per-cell MHWs
# For each sea cell:
#   1. Find runs of >= 5 consecutive hot days
#   2. Join runs separated by 1-2 non-hot days
# The joining is done after finding initial runs, and gap days become part of the MHW

# Per-cell MHW mask: (n_target, n_lat, n_lon) - 1 if inside a per-cell MHW
per_cell_mhw = np.zeros((n_target, n_lat, n_lon), dtype=bool)

# Find sea cell indices
sea_idx = np.argwhere(sea_cells)
print(f"Processing {len(sea_idx)} sea cells for MHW detection...")

for si, (i, j) in enumerate(sea_idx):
    # Get hot days for this cell
    hot_cell = hot[:, i, j]
    
    # Find runs of consecutive hot days
    # First, find initial runs
    runs = []  # list of (start, end) tuples
    
    t = 0
    while t < n_target:
        if hot_cell[t]:
            # Start of a potential run
            start = t
            while t < n_target and hot_cell[t]:
                t += 1
            end = t - 1  # inclusive
            runs.append((start, end))
        else:
            t += 1
    
    # Filter runs to those with length >= 5
    runs = [(s, e) for s, e in runs if (e - s + 1) >= 5]
    
    # Join runs separated by 1-2 non-hot days
    if len(runs) > 1:
        joined = [runs[0]]
        for r in runs[1:]:
            prev_s, prev_e = joined[-1]
            if r[0] - prev_e - 1 <= 2:  # gap of 1 or 2 days
                # Join
                joined[-1] = (prev_s, r[1])
            else:
                joined.append(r)
        runs = joined
    
    # Mark per-cell MHW days
    for s, e in runs:
        per_cell_mhw[s:e+1, i, j] = True
    
    if (si + 1) % 1000 == 0:
        print(f"  Processed {si+1}/{len(sea_idx)}")

print(f"Per-cell MHW days: {per_cell_mhw.sum()}")

# Regional events
# A day is active if at least one sea cell is inside a per-cell MHW
active = np.any(per_cell_mhw, axis=(1, 2))
print(f"Active days: {active.sum()}")

# Find regional MHW events (maximal runs of consecutive active days)
events = []
t = 0
while t < n_target:
    if active[t]:
        start = t
        while t < n_target and active[t]:
            t += 1
        end = t - 1
        events.append((start, end))
    else:
        t += 1

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]}")

# Save per-cell MHW mask
np.save('/tmp/work/per_cell_mhw.npy', per_cell_mhw)
np.save('/tmp/work/active_days.npy', active)
with open('/tmp/work/events.pkl', 'wb') as f:
    pickle.dump(events, f)

print("\nDone computing MHWs.")
