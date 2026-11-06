import numpy as np
from datetime import date, timedelta
import pickle

# Reload all saved data
target_sst = np.load('/tmp/work/target_sst.npy')
with open('/tmp/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
sea_cells = np.load('/tmp/work/sea_cells.npy')
threshold_smooth = np.load('/tmp/work/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/work/climatology_smooth.npy')
saved_per_cell_mhw = np.load('/tmp/work/per_cell_mhw.npy')

n_target, n_lat, n_lon = target_sst.shape

def month_day_to_doy(month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Recompute hot days
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for t in range(n_target):
    d = target_dates[t]
    doy = month_day_to_doy(d.month, d.day)
    thresh = threshold_smooth[doy-1]
    hot[t] = (target_sst[t] >= thresh) & sea_cells

# Recompute per-cell MHWs
per_cell_mhw = np.zeros((n_target, n_lat, n_lon), dtype=bool)
sea_idx = np.argwhere(sea_cells)

for i, j in sea_idx:
    hot_cell = hot[:, i, j]
    
    # Find runs of consecutive hot days
    runs = []
    t = 0
    while t < n_target:
        if hot_cell[t]:
            start = t
            while t < n_target and hot_cell[t]:
                t += 1
            end = t - 1
            runs.append((start, end))
        else:
            t += 1
    
    # Filter to runs >= 5
    runs = [(s, e) for s, e in runs if (e - s + 1) >= 5]
    
    # Join runs separated by 1-2 non-hot days
    if len(runs) > 1:
        joined = [runs[0]]
        for r in runs[1:]:
            prev_s, prev_e = joined[-1]
            if r[0] - prev_e - 1 <= 2:
                joined[-1] = (prev_s, r[1])
            else:
                joined.append(r)
        runs = joined
    
    # Mark per-cell MHW days
    for s, e in runs:
        per_cell_mhw[s:e+1, i, j] = True

# Compare with saved
print(f"Saved per-cell MHW sum: {saved_per_cell_mhw.sum()}")
print(f"Recomputed per-cell MHW sum: {per_cell_mhw.sum()}")
print(f"Match: {np.array_equal(saved_per_cell_mhw, per_cell_mhw)}")

# Recompute regional events
active = np.any(per_cell_mhw, axis=(1, 2))
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

print(f"Events: {events}")
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]}")
