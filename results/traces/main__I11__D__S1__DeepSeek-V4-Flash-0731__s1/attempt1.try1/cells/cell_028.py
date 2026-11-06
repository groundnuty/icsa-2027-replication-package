
import numpy as np
import json
import pandas as pd
from datetime import date

# Load mhw_mask
mhw_mask = np.load('/work/mhw_mask.npy')

# Reload target dates
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values
target_idx = np.where((time_vals >= np.datetime64('2021-06-01')) & (time_vals <= np.datetime64('2021-08-31')))[0]
target_time = time_vals[target_idx]
target_dates = [pd.Timestamp(t).date() for t in target_time]

# Find active days
active = mhw_mask.sum(axis=(1, 2)) > 0
active_indices = np.where(active)[0]
print(f"Active days: {len(active_indices)}")
print(f"Active indices: {active_indices}")

# Find maximal runs
if len(active_indices) == 0:
    events = []
else:
    events = []
    start = active_indices[0]
    prev = active_indices[0]
    for d in active_indices[1:]:
        if d > prev + 1:
            events.append((start, prev))
            start = d
        prev = d
    events.append((start, prev))

print(f"Events: {events}")

event_list = []
for s, e in events:
    onset = target_dates[s].isoformat()
    end = target_dates[e].isoformat()
    event_list.append({"onset": onset, "end": end})
    print(f"Event: {onset} to {end}")

# Create report
report = {
    "region": {
        "lat_min": 55.67,
        "lat_max": 56.87,
        "lon_min": 16.45,
        "lon_max": 17.65
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2021-06-01",
        "end": "2021-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\nWrote output/report.json")
print(json.dumps(report, indent=2))
