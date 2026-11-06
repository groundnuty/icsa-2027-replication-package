
import numpy as np
from datetime import datetime

def doy_fixed(dt):
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month - 1] + dt.day

# Load data
target_sst = np.load('/work/target_sst.npy')
target_times = np.load('/work/target_times.npy')
sea_cells = np.load('/work/sea_cells.npy')
threshold_smooth = np.load('/work/threshold_smooth.npy')

# Get target dates
target_dates = []
for t in target_times:
    dt = datetime.utcfromtimestamp(t.astype('datetime64[s]').astype(np.int64))
    target_dates.append(dt)
target_dates = np.array(target_dates)

target_doy = np.array([doy_fixed(d) for d in target_dates])

n_sea = sea_cells.sum()
target_sst_sea = target_sst[:, sea_cells]

# Compute hot mask
hot = np.zeros((len(target_dates), n_sea), dtype=bool)
for t_idx, doy in enumerate(target_doy):
    hot[t_idx, :] = target_sst_sea[t_idx, :] >= threshold_smooth[:, doy-1]

n_days, n_sea = hot.shape

# Find per-cell MHWs
cell_mhw = np.zeros_like(hot, dtype=bool)

for c in range(n_sea):
    h = hot[:, c]
    
    # Find runs of hot days
    runs = []
    i = 0
    while i < n_days:
        if h[i]:
            start = i
            while i < n_days and h[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    if not runs:
        continue
    
    # Join runs separated by 1-2 non-hot days
    joined = [runs[0]]
    for r in runs[1:]:
        prev = joined[-1]
        gap = r[0] - prev[1] - 1
        if gap <= 2:
            joined[-1] = (prev[0], r[1])
        else:
            joined.append(r)
    
    # Keep runs of at least 5 days
    for start, end in joined:
        if end - start + 1 >= 5:
            cell_mhw[start:end+1, c] = True

print("Per-cell MHW days:", cell_mhw.sum())
print("Cells with at least one MHW:", (cell_mhw.sum(axis=0) > 0).sum())

# Regional events:
# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = cell_mhw.sum(axis=1) > 0
print("Active days:", active.sum())

# Regional MHW events are maximal runs of consecutive active days
events = []
i = 0
while i < n_days:
    if active[i]:
        start = i
        while i < n_days and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print("Regional events:", len(events))
for s, e in events:
    print(f"  {target_dates[s].date()} to {target_dates[e].date()} ({e-s+1} days)")
