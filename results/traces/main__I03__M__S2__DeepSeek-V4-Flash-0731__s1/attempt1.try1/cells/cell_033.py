
import json
import numpy as np
from datetime import datetime, date, timedelta
import xarray as xr

# Load data for event dates
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
time = ds['time'].values
target_time_idx = np.load('/tmp/target_time_idx.npy')
mhw_mask = np.load('/tmp/mhw_mask_correct.npy')

# Target dates
target_dates = []
for i in target_time_idx:
    t = time[i]
    dt = datetime.utcfromtimestamp(int(t) / 1e9)
    target_dates.append(dt.date())

# Compute events
active = mhw_mask.sum(axis=(1, 2)) > 0
events = []
in_event = False
start = 0
for i in range(len(active)):
    if active[i] and not in_event:
        start = i
        in_event = True
    elif not active[i] and in_event:
        events.append((start, i-1))
        in_event = False
if in_event:
    events.append((start, len(active)-1))

event_list = []
for e in events:
    onset = target_dates[e[0]]
    end = target_dates[e[1]]
    event_list.append({
        "onset": onset.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d")
    })

print("Events:", json.dumps(event_list, indent=2))

# Build report
report = {
    "region": {
        "lat_min": 54.17,
        "lat_max": 55.37,
        "lon_min": 13.25,
        "lon_max": 14.45
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

print("\nWrote output/report.json")
print(json.dumps(report, indent=2))
