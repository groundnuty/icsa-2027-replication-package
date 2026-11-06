
import numpy as np
import datetime
import json

# Load corrected MHW mask
mhw_mask = np.load('/tmp/mhw_mask_corrected.npy')  # (92, 60, 60)

# Load target dates
target_times = np.load('/tmp/target_times.npy')
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

# Regional events
active = mhw_mask.sum(axis=(1, 2)) > 0
print(f"Active days: {active.sum()} out of {len(active)}")

# Find maximal runs of consecutive active days
events = []
start = None
for t in range(len(active)):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t-1))
            start = None
if start is not None:
    events.append((start, len(active)-1))

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]}, length={e-s+1} days")
