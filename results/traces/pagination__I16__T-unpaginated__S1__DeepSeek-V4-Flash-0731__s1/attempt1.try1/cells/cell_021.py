
import numpy as np
from datetime import date, timedelta

hot = np.load('/tmp/hot.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Target dates
target_start = date(2008, 6, 1)
target_end = date(2008, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

# Recompute per-cell MHWs for all cells
n_days = hot.shape[0]
n_cells = hot.shape[1]

mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for c in range(n_cells):
    hot_series = hot[:, c].astype(bool)
    
    # Find runs of consecutive hot days
    runs = []
    i = 0
    while i < n_days:
        if hot_series[i]:
            start = i
            while i < n_days and hot_series[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    # Filter runs >= 5 days
    runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    
    if not runs:
        continue
    
    # Join runs separated by 1 or 2 non-hot days
    joined = []
    current = runs[0]
    for next_run in runs[1:]:
        gap = next_run[0] - current[1] - 1
        if 1 <= gap <= 2:
            current = (current[0], next_run[1])
        else:
            joined.append(current)
            current = next_run
    joined.append(current)
    
    # Mark MHW days
    for start, end in joined:
        mhw_mask[start:end+1, c] = 1

# Regional events
active_days = np.any(mhw_mask > 0, axis=1)
print('Active days:', np.where(active_days)[0])
print('Active days count:', active_days.sum())

# Show which cells are in MHW on each active day
for t in range(n_days):
    if active_days[t]:
        n_cells_in_mhw = np.sum(mhw_mask[t] > 0)
        print(f'  Day {t} ({target_dates[t]}): {n_cells_in_mhw} cells in MHW')

# For each active day, show which cells
for t in np.where(active_days)[0]:
    cells_in_mhw = np.where(mhw_mask[t] > 0)[0]
    print(f'  Day {t} ({target_dates[t]}): {len(cells_in_mhw)} cells, first 10: {cells_in_mhw[:10]}')

# Find regional events
events = []
i = 0
while i < n_days:
    if active_days[i]:
        start = i
        while i < n_days and active_days[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print('\nRegional events:')
for start, end in events:
    print(f'  {target_dates[start]} to {target_dates[end]}, length {end-start+1} days')

np.save('/tmp/mhw_mask.npy', mhw_mask)
print('\nSaved mhw_mask')
