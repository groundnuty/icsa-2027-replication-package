
import numpy as np
import pickle
import datetime as dt

# Load state
sea_cells = np.load('/work/sea_cells.npy')
target_sst = np.load('/work/target_sst.npy')
threshold_smoothed = np.load('/work/threshold_smoothed.npy')
climatology_smoothed = np.load('/work/climatology_smoothed.npy')

with open('/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
lats = np.load('/work/lats.npy')
lons = np.load('/work/lons.npy')

n_lat, n_lon = sea_cells.shape
n_target = len(target_dates)
print(f"Target days: {n_target}, grid: {n_lat}x{n_lon}")

# Compute day of year for each target day
def day_of_year(date):
    month = date.month
    day = date.day
    cum_days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_before[month - 1] + day

target_doy = [day_of_year(d) for d in target_dates]
print(f"Target DOY range: {min(target_doy)} to {max(target_doy)}")

# ============================================================
# Step 3: Per-cell MHWs
# ============================================================
# For each sea cell, determine hot days
# mhw_mask: (n_target, n_lat, n_lon) - 1 if inside per-cell MHW
mhw_mask = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

sea_idx = np.where(sea_cells)
n_sea = len(sea_idx[0])

for k in range(n_sea):
    i, j = sea_idx[0][k], sea_idx[1][k]
    
    # Get SST and threshold for this cell over target period
    sst_cell = target_sst[:, i, j]  # (n_target,)
    thr_cell = np.array([threshold_smoothed[doy - 1, i, j] for doy in target_doy])  # (n_target,)
    
    # Hot day check: sst >= threshold
    hot = np.zeros(n_target, dtype=bool)
    for t in range(n_target):
        if np.isfinite(sst_cell[t]) and np.isfinite(thr_cell[t]):
            hot[t] = sst_cell[t] >= thr_cell[t]
    
    # Find runs of at least 5 consecutive hot days
    # Then join runs separated by 1-2 non-hot days
    
    # First find all runs
    runs = []
    in_run = False
    run_start = 0
    for t in range(n_target):
        if hot[t] and not in_run:
            in_run = True
            run_start = t
        elif not hot[t] and in_run:
            in_run = False
            runs.append((run_start, t - 1))
    if in_run:
        runs.append((run_start, n_target - 1))
    
    # Filter to runs of >= 5 days
    long_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    # Join runs separated by 1 or 2 non-hot days
    if long_runs:
        merged_runs = [long_runs[0]]
        for s, e in long_runs[1:]:
            prev_s, prev_e = merged_runs[-1]
            gap = s - prev_e - 1
            if gap <= 2:
                # Merge
                merged_runs[-1] = (prev_s, e)
            else:
                merged_runs.append((s, e))
        
        # Mark mask
        for s, e in merged_runs:
            mhw_mask[s:e+1, i, j] = 1

print(f"Per-cell MHW mask computed")
print(f"Active cells on first day: {np.sum(mhw_mask[0])}")
print(f"Active cells on last day: {np.sum(mhw_mask[-1])}")

# ============================================================
# Step 4: Regional events
# ============================================================
# A day is active if at least one sea cell is inside a per-cell MHW
active = np.any(mhw_mask > 0, axis=(1, 2))  # (n_target,)

print(f"Active days: {np.sum(active)} out of {n_target}")
for t in range(n_target):
    if active[t]:
        print(f"  {target_dates[t].date()}: active")

# Find maximal runs of consecutive active days
events = []
in_event = False
event_start = 0
for t in range(n_target):
    if active[t] and not in_event:
        in_event = True
        event_start = t
    elif not active[t] and in_event:
        in_event = False
        events.append((event_start, t - 1))
if in_event:
    events.append((event_start, n_target - 1))

print(f"\nRegional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s].date()} to {target_dates[e].date()}")

# Save
np.save('/work/mhw_mask.npy', mhw_mask)
np.save('/work/active.npy', active)

# Save events
with open('/work/events.pkl', 'wb') as f:
    pickle.dump(events, f)
