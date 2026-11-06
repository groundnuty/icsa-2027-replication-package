
import numpy as np
import xarray as xr
import json
import pandas as pd
import os

# Load data
per_cell_mhw = np.load('per_cell_mhw.npy')
sea_cells = np.load('sea_cells.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')
lats = np.load('lats.npy')
lons = np.load('lons.npy')

print('Shapes:', per_cell_mhw.shape, lats.shape, lons.shape)
print('Target time:', target_time[0], target_time[-1])
print('Lat range:', lats[0], lats[-1])
print('Lon range:', lons[0], lons[-1])

# Create output directory
os.makedirs('output', exist_ok=True)

# Create mhw mask as uint8
mhw_mask = per_cell_mhw.astype(np.uint8)

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': target_time,
        'lat': lats,
        'lon': lons
    }
)

# Write NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print('Wrote mhw_mask.nc')

# Write report.json
# Find events
active = np.zeros(len(target_time), dtype=bool)
for t in range(len(target_time)):
    active[t] = np.any(per_cell_mhw[t] & sea_cells)

events = []
in_event = False
for t in range(len(active)):
    if active[t]:
        if not in_event:
            start = t
            in_event = True
    else:
        if in_event:
            events.append((start, t - 1))
            in_event = False
if in_event:
    events.append((start, len(active) - 1))

event_list = []
for s, e in events:
    onset = pd.Timestamp(target_time[s]).strftime('%Y-%m-%d')
    end = pd.Timestamp(target_time[e]).strftime('%Y-%m-%d')
    event_list.append({'onset': onset, 'end': end})

report = {
    'region': {
        'lat_min': float(lats[0]),
        'lat_max': float(lats[-1]),
        'lon_min': float(lons[0]),
        'lon_max': float(lons[-1])
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2019-06-01',
        'end': '2019-08-31'
    },
    'events': event_list,
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print('Wrote report.json')
print(json.dumps(report, indent=2))
