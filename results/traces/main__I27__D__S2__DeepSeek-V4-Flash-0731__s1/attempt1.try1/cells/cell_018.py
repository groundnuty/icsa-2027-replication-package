
import numpy as np
import pandas as pd

mhw_mask = np.load('/work/mhw_mask.npy')
target_time = np.load('/work/target_time.npy').astype('datetime64[D]')

ntarget = mhw_mask.shape[0]

# Day is active if at least one sea cell is in an MHW
active = mhw_mask.sum(axis=(1, 2)) > 0
print("Active days indices:", np.where(active)[0])

# Print for each active day which date and how many cells
for d in np.where(active)[0]:
    n_cells = mhw_mask[d].sum()
    print(f"Day {d}: {pd.Timestamp(target_time[d]).strftime('%Y-%m-%d')} - {n_cells} cells in MHW")

# Find regional events
events = []
in_event = False
event_start = 0
for d in range(ntarget):
    if active[d] and not in_event:
        in_event = True
        event_start = d
    elif not active[d] and in_event:
        in_event = False
        events.append((event_start, d-1))
if in_event:
    events.append((event_start, ntarget-1))

print("\nRegional events:")
for start, end in events:
    print(f"  {pd.Timestamp(target_time[start]).strftime('%Y-%m-%d')} to {pd.Timestamp(target_time[end]).strftime('%Y-%m-%d')} (days {start}-{end})")
