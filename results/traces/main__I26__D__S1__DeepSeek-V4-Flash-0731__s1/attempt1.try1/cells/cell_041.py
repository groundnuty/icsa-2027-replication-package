import numpy as np
from datetime import datetime, timedelta

# Load data
target_data = np.load('/work/target_data.npy').astype(np.float64)
threshold_smooth = np.load('/work/threshold_smooth.npy')

def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

target_dates = []
d = datetime(2007, 6, 1)
while d <= datetime(2007, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

target_doy = np.array([day_of_year(dt.month, dt.day) for dt in target_dates])

sea_mask = np.all(~np.isnan(target_data), axis=0)

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

# Compute per-cell MHW mask
cell_mhw_mask = np.zeros((92, 60, 60), dtype=bool)
for i in range(60):
    for j in range(60):
        if sea_mask[i, j]:
            cell_mhw_mask[:, i, j] = detect_cell_mhw(hot[:, i, j])

# Regional events: day is active if >=1 sea cell in MHW
active = np.any(cell_mhw_mask, axis=(1, 2))
print("Active days:", np.sum(active))
for t in range(92):
    if active[t]:
        print(f"  Day {t} ({target_dates[t].date()}): active")

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

print(f"\nRegional events: {len(events)}")
for s, e in events:
    print(f"  Event: {target_dates[s].date()} to {target_dates[e].date()} ({e-s+1} days)")
