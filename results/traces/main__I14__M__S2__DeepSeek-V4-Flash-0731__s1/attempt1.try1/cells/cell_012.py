
import numpy as np
import pandas as pd

# Load
mhw_mask = np.load('/tmp/mhw_mask.npy')  # (n_sea, n_target)
sea_cells = np.load('/tmp/sea_cells.npy')
target_indices = np.load('/tmp/target_indices.npy')

times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')

# Regional events
# A day is active if at least one sea cell is in a per-cell MHW
active = (mhw_mask.sum(axis=0) > 0).astype(np.int8)
print("Active days:", active.sum(), "out of", len(active))

# Find maximal runs of consecutive active days
events = []
i = 0
n_target = len(active)
while i < n_target:
    if active[i] == 1:
        j = i
        while j < n_target and active[j] == 1:
            j += 1
        events.append((i, j - 1))
        i = j
    else:
        i += 1

print("Number of regional events:", len(events))
for start, end in events:
    print(f"  Event: {times[target_indices[start]].date()} to {times[target_indices[end]].date()} (length {end-start+1} days)")

# Format events
event_list = []
for start, end in events:
    event_list.append({
        "onset": str(times[target_indices[start]].date()),
        "end": str(times[target_indices[end]].date())
    })

print("\nEvents:", event_list)
