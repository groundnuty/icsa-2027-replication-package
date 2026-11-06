
import numpy as np
import json
import os
from datetime import date, timedelta

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')
tgt_time = np.load('/work/tgt_time.npy')
lat_vals = np.load('/work/lat_vals.npy')
lon_vals = np.load('/work/lon_vals.npy')

target_dates = [date(1970,1,1) + timedelta(days=int(t)) for t in tgt_time]

# Determine regional events
active = mhw_mask.any(axis=(1,2))
events = []
i = 0
n_t = len(active)
while i < n_t:
    if active[i]:
        start = i
        while i < n_t and active[i]:
            i += 1
        events.append((start, i-1))
    else:
        i += 1

# Build report
report = {
    "region": {
        "lat_min": 64.39,
        "lat_max": 65.59,
        "lon_min": 23.41,
        "lon_max": 24.61
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2019-06-01",
        "end": "2019-08-31"
    },
    "events": [
        {"onset": target_dates[s].isoformat(), "end": target_dates[e].isoformat()}
        for s, e in events
    ],
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
print("\nReport written to output/report.json")
