
import numpy as np
import pandas as pd

per_cell_mhw = np.load('per_cell_mhw.npy')
sea_cells = np.load('sea_cells.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')

# Active days: at least one sea cell in a per-cell MHW
active = np.zeros(per_cell_mhw.shape[0], dtype=bool)
for t in range(per_cell_mhw.shape[0]):
    active[t] = np.any(per_cell_mhw[t] & sea_cells)

print('Active days:', active.sum(), 'out of', len(active))

# Find maximal runs of consecutive active days
events = []
in_event = False
for t in range(len(active)):
    if active[t]:
        if not in_event:
            start = t
            in_event = True
    else:
        if in_event:
            events.append((start, t - 1))
            in_event = False
if in_event:
    events.append((start, len(active) - 1))

print('Number of regional events:', len(events))
for s, e in events:
    print(f'  {pd.Timestamp(target_time[s]).strftime("%Y-%m-%d")} to {pd.Timestamp(target_time[e]).strftime("%Y-%m-%d")} ({e-s+1} days)')
