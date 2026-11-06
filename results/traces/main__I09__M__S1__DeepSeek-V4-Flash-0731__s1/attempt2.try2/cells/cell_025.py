
import numpy as np
from datetime import date, timedelta
import json

# Load data
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

n_days, n_lat, n_lon = mhw_mask.shape

# Target dates
target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

# Determine active days
active = np.any(mhw_mask & sea_cells[np.newaxis, :, :], axis=(1, 2))

# Find maximal runs of active days
events = []
in_event = False
event_start = 0
for t in range(n_days):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, n_days - 1))

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s].isoformat()} to {target_dates[e].isoformat()}")

# Build report
report = {
    "region": {
        "lat_min": 54.81,
        "lat_max": 56.01,
        "lon_min": 19.61,
        "lon_max": 20.81
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2022-06-01",
        "end": "2022-08-31"
    },
    "events": [
        {"onset": target_dates[s].isoformat(), "end": target_dates[e].isoformat()}
        for s, e in events
    ],
    "complete": True,
    "caveats": ""
}

print(json.dumps(report, indent=2))

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\nReport written successfully")
