
import numpy as np
import pandas as pd

# Load MHW mask
mhw_mask = np.load('/work/mhw_mask.npy')
sea_cells = np.load('/work/sea_cells.npy')

print(f"MHW mask shape: {mhw_mask.shape}")
print(f"Total MHW cell-days: {mhw_mask.sum()}")

# A day is active if at least one sea cell is inside a per-cell MHW
# Note: we only consider sea cells
active = np.zeros(mhw_mask.shape[0], dtype=bool)
for t in range(mhw_mask.shape[0]):
    # Only check sea cells
    active[t] = np.any(mhw_mask[t][sea_cells] == 1)

print(f"Active days: {active.sum()} out of {len(active)}")
print(f"Active day indices: {np.where(active)[0]}")

# Find maximal runs of consecutive active days
events = []
in_event = False
event_start = 0

n_time = len(active)
for t in range(n_time):
    if active[t] and not in_event:
        in_event = True
        event_start = t
    elif not active[t] and in_event:
        in_event = False
        events.append((event_start, t-1))
if in_event:
    events.append((event_start, n_time-1))

print(f"\nRegional events: {len(events)}")
for start, end in events:
    print(f"  Event: days {start}-{end}")
