
import numpy as np
import datetime

# Load data
target_sst = np.load('target_sst.npy')  # shape (92, 60, 60)
sea_cells = np.load('sea_cells.npy')
threshold_smooth = np.load('threshold_smooth.npy')  # shape (366, 60, 60)

# Target dates
target_start = datetime.date(2007, 6, 1)
target_dates = []
d = target_start
for i in range(92):
    target_dates.append(d)
    d += datetime.timedelta(days=1)

# Define doy function
def date_to_doy(d):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = d.day
    for m in range(1, d.month):
        doy += days_in_month[m-1]
    return doy

# Get doy for each target date
target_doys = [date_to_doy(d) for d in target_dates]
print(f"Target doys: {target_doys[0]} to {target_doys[-1]}")

# For each sea cell and target day, determine hot/cold
# hot[i, j, t] = True if SST >= threshold
n_t, n_lat, n_lon = target_sst.shape
hot = np.zeros((n_t, n_lat, n_lon), dtype=bool)

for t in range(n_t):
    doy = target_doys[t]
    thr = threshold_smooth[doy-1]  # threshold for this doy
    hot[t] = (target_sst[t] >= thr) & np.isfinite(target_sst[t])

print(f"Hot cells per day (first 10):")
for t in range(10):
    print(f"  Day {t} ({target_dates[t]}): {hot[t].sum()} hot cells")

# Now find per-cell MHWs
# For each sea cell, find runs of at least 5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

mhw_mask = np.zeros((n_t, n_lat, n_lon), dtype=np.uint8)

sea_indices = np.argwhere(sea_cells)
print(f"\nProcessing {len(sea_indices)} sea cells")

for idx in sea_indices:
    i, j = idx
    hot_series = hot[:, i, j]
    
    # Find hot runs (consecutive True)
    runs = []
    in_run = False
    start = 0
    for t in range(n_t):
        if hot_series[t] and not in_run:
            in_run = True
            start = t
        elif not hot_series[t] and in_run:
            in_run = False
            runs.append((start, t-1))
    if in_run:
        runs.append((start, n_t-1))
    
    if not runs:
        continue
    
    # Find runs of at least 5 days
    valid_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if not valid_runs:
        continue
    
    # Join runs separated by 1-2 non-hot days
    # First, identify which target days belong to MHWs
    in_mhw = np.zeros(n_t, dtype=bool)
    
    # Mark all days in valid_runs as in MHW
    for s, e in valid_runs:
        in_mhw[s:e+1] = True
    
    # Now fill gaps of 1-2 days between MHW runs
    # Find the actual MHW intervals (after joining)
    # A simpler approach: find all valid runs, then join those separated by 1-2 days
    # We need to be careful: the joining might chain (e.g., run1-gap-run2-gap-run3)
    
    # Let's use a different approach
    # Find the joined intervals
    joined = []
    current_start = valid_runs[0][0]
    current_end = valid_runs[0][1]
    
    for s, e in valid_runs[1:]:
        if s - current_end <= 3:  # gap of 1 or 2 days
            current_end = e
        else:
            joined.append((current_start, current_end))
            current_start = s
            current_end = e
    joined.append((current_start, current_end))
    
    # Mark all days in joined intervals as in MHW
    for s, e in joined:
        mhw_mask[s:e+1, i, j] = 1

print(f"MHW mask: {mhw_mask.sum()} cell-days marked as MHW")

np.save('mhw_mask.npy', mhw_mask)
print("Saved MHW mask")
