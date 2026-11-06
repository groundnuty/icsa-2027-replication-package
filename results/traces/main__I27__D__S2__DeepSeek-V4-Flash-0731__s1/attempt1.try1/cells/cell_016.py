
import numpy as np
import pandas as pd

mhw_mask = np.load('/work/mhw_mask.npy')
target_time = np.load('/work/target_time.npy').astype('datetime64[D]')

ntarget = mhw_mask.shape[0]

# Day is active if at least one sea cell is in an MHW
active = mhw_mask.sum(axis=(1, 2)) > 0  # (ntarget,)
print("Active days:", active.sum(), "out of", ntarget)

# Find regional events (maximal runs of consecutive active days)
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

print("Number of regional events:", len(events))

# Format events
event_list = []
for start, end in events:
    onset = pd.Timestamp(target_time[start]).strftime('%Y-%m-%d')
    end_date = pd.Timestamp(target_time[end]).strftime('%Y-%m-%d')
    event_list.append({"onset": onset, "end": end_date})
    print(f"Event: {onset} to {end_date}")

# Save events
import json
with open('/work/events.json', 'w') as f:
    json.dump(event_list, f, indent=2)
