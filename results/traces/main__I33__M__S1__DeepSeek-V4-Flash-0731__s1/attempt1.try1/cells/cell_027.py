
import json
import numpy as np
from datetime import datetime, timezone

# Determine regional events
mhw_mask = np.load('output/mhw_mask.npy')
target_dates = np.load('output/target_dates.npy')

n_days = mhw_mask.shape[0]
active = mhw_mask.sum(axis=(1, 2)) > 0

events = []
i = 0
while i < n_days:
    if active[i]:
        start = i
        while i < n_days and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

# Convert events to date strings
event_list = []
for start, end in events:
    ts1 = target_dates[start].astype('datetime64[ns]').astype(np.int64) / 1e9
    ts2 = target_dates[end].astype('datetime64[ns]').astype(np.int64) / 1e9
    onset = datetime.fromtimestamp(ts1, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(ts2, tz=timezone.utc)
    event_list.append({
        "onset": onset.strftime('%Y-%m-%d'),
        "end": end_dt.strftime('%Y-%m-%d')
    })

print(f"Events: {event_list}")

# Create report
report = {
    "region": {
        "lat_min": 59.05,
        "lat_max": 60.25,
        "lon_min": 21.25,
        "lon_max": 22.45
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2014-06-01",
        "end": "2014-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Saved report.json")
print(json.dumps(report, indent=2))
