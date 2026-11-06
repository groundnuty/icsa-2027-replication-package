import json
import numpy as np
from datetime import datetime, timedelta

# Load data
cell_mhw_mask = np.load('/work/cell_mhw_mask.npy')

# Regional events
active = np.any(cell_mhw_mask, axis=(1, 2))

# Target dates
target_dates = []
d = datetime(2007, 6, 1)
while d <= datetime(2007, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Find maximal runs of consecutive active days
events = []
in_event = False
for t in range(92):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, 91))

event_list = []
for s, e in events:
    onset = target_dates[s].strftime('%Y-%m-%d')
    end = target_dates[e].strftime('%Y-%m-%d')
    event_list.append({"onset": onset, "end": end})

print("Events:", event_list)

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
        "start": "2007-06-01",
        "end": "2007-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("report.json written")
print(json.dumps(report, indent=2))
