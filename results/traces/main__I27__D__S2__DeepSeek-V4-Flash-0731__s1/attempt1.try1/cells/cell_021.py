
import numpy as np
import pandas as pd
import json
import os

# Load events
mhw_mask = np.load('/work/mhw_mask.npy')
target_time = np.load('/work/target_time.npy').astype('datetime64[D]')

ntarget = mhw_mask.shape[0]
active = mhw_mask.sum(axis=(1, 2)) > 0

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

# Format events
event_list = []
for start, end in events:
    onset = pd.Timestamp(target_time[start]).strftime('%Y-%m-%d')
    end_date = pd.Timestamp(target_time[end]).strftime('%Y-%m-%d')
    event_list.append({"onset": onset, "end": end_date})

print("Events:", event_list)

# Create report
report = {
    "region": {
        "lat_min": 57.83,
        "lat_max": 59.03,
        "lon_min": 17.41,
        "lon_max": 18.61
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2008-06-01",
        "end": "2008-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Written report.json")
with open('output/report.json', 'r') as f:
    print(f.read())
