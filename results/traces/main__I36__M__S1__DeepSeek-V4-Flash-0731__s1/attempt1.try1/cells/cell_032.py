
import json
import numpy as np
from datetime import date

# Load cell_mhw and target dates
cell_mhw = np.load('/tmp/cell_mhw.npy')
with open('/tmp/target_dates.txt') as f:
    target_dates_str = [line.strip() for line in f]
target_dates = [date.fromisoformat(s) for s in target_dates_str]

# Regional events
n_days = len(target_dates)
active = cell_mhw.any(axis=(1, 2))

events = []
start = None
for t in range(n_days):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t-1))
            start = None
if start is not None:
    events.append((start, n_days-1))

event_list = []
for s, e in events:
    event_list.append({
        "onset": target_dates[s].isoformat(),
        "end": target_dates[e].isoformat()
    })

report = {
    "region": {
        "lat_min": 60.09,
        "lat_max": 61.29,
        "lon_min": 20.01,
        "lon_max": 21.21
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2003-06-01",
        "end": "2003-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print(json.dumps(report, indent=2))
