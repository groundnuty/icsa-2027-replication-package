
import numpy as np
import pandas as pd
import json
import xarray as xr

# Reload for events
mhw_mask = np.load('/work/mhw_mask.npy')

# Active days
active = mhw_mask.any(axis=(0, 1))

# Find regional events
runs = []
t = 0
n_time = len(active)
while t < n_time:
    if active[t]:
        start = t
        while t < n_time and active[t]:
            t += 1
        end = t - 1
        runs.append((start, end))
    else:
        t += 1

# Get dates
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))
target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_dates = pd.to_datetime(target.time.values).date

events = []
for start, end in runs:
    events.append({
        'onset': str(target_dates[start]),
        'end': str(target_dates[end])
    })

print("Events:", events)

# Build report
report = {
    'region': {
        'lat_min': 55.67,
        'lat_max': 56.87,
        'lon_min': 16.45,
        'lon_max': 17.65
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2021-06-01',
        'end': '2021-08-31'
    },
    'events': events,
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
