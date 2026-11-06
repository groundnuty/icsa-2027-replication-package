
import json
import numpy as np
from datetime import date, timedelta

# Load per-cell MHW data to determine events
per_cell_mhw = np.load('per_cell_mhw.npy')

target_dates = []
d = date(2015, 6, 1)
while d <= date(2015, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Regional events
active = np.any(per_cell_mhw, axis=(1, 2))
events = []
i = 0
while i < len(active):
    if active[i]:
        start = i
        while i < len(active) and active[i]:
            i += 1
        events.append((start, i-1))
    else:
        i += 1

event_list = []
for s, e in events:
    event_list.append({
        "onset": target_dates[s].isoformat(),
        "end": target_dates[e].isoformat()
    })

print(f"Events: {event_list}")

report = {
    "region": {
        "lat_min": 56.13,
        "lat_max": 57.33,
        "lon_min": 17.71,
        "lon_max": 18.91
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2015-06-01",
        "end": "2015-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Written output/report.json")
print(json.dumps(report, indent=2))
