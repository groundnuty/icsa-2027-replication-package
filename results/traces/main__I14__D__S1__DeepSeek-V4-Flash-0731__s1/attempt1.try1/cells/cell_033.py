
import numpy as np
import pandas as pd
import json

# Load per-cell MHW data
target_times = np.load('/work/target_times.npy')
target_pd = pd.to_datetime(target_times)
per_cell_mhw = np.load('/work/per_cell_mhw.npy')

# Regional events
active = np.any(per_cell_mhw, axis=(1, 2))
events = []
i = 0
n_time = len(target_pd)
while i < n_time:
    if active[i]:
        j = i
        while j < n_time and active[j]:
            j += 1
        events.append({
            'onset': str(target_pd[i].date()),
            'end': str(target_pd[j-1].date())
        })
        i = j
    else:
        i += 1

print("Events:", events)

# Build report
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
    "events": events,
    "complete": True,
    "caveats": ""
}

with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Written report.json")
print(json.dumps(report, indent=2))
