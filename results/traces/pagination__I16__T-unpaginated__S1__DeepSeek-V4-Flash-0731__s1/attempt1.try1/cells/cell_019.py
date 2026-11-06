
import numpy as np

hot = np.load('/tmp/hot.npy')  # (92, 3600)
sea_cells = np.load('/tmp/sea_cells.npy')  # (3600,)

# Per-cell MHW mask: 1 if cell is inside a per-cell MHW on that day, 0 otherwise
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

n_days = hot.shape[0]
n_cells = hot.shape[1]

for c in range(n_cells):
    if not sea_cells[c]:
        continue
    
    hot_series = hot[:, c].astype(bool)
    
    # Find runs of consecutive hot days
    runs = []  # list of (start, end) inclusive
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
            # Join
            current = (current[0], next_run[1])
        else:
            joined.append(current)
            current = next_run
    joined.append(current)
    
    # Mark MHW days
    for start, end in joined:
        mhw_mask[start:end+1, c] = 1

print('MHW mask shape:', mhw_mask.shape)
print('Number of cell-days in MHWs:', mhw_mask.sum())

# Regional events
active_days = np.any(mhw_mask > 0, axis=1)  # (92,)
print('Active days:', active_days.sum(), 'out of', n_days)

# Find maximal runs of active days
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

print('Number of regional events:', len(events))
for start, end in events:
    print(f'  Event: day {start} to {end} (inclusive), length {end-start+1}')
