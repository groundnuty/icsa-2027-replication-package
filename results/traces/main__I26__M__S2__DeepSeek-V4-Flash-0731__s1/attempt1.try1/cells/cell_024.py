
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict
import json
import xarray as xr
import os

# Load all intermediate results
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')  # (92, 60, 60) uint8/bool
sea_cells = np.load('/tmp/sea_cells.npy')
tgt_doy = np.load('/tmp/tgt_doy.npy')

# Get time and coordinate values
path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

time_all = ds.time.values
tgt_start_idx = 9282
tgt_end_idx = 9373
tgt_time = time_all[tgt_start_idx:tgt_end_idx+1]

lat_vals = ds.latitude.values[217:277]
lon_vals = ds.longitude.values[421:481]

ds.close()

print(f"Target time: {tgt_time[0]} to {tgt_time[-1]}, {len(tgt_time)} days")
print(f"Lat values: {lat_vals[0]} to {lat_vals[-1]}")
print(f"Lon values: {lon_vals[0]} to {lon_vals[-1]}")

# Determine active days for regional events
active = per_cell_mhw.any(axis=(1, 2))

# Find regional events
events = []
in_event = False
for t in range(len(tgt_time)):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t-1))
            in_event = False
if in_event:
    events.append((event_start, len(tgt_time)-1))

print(f"\nRegional events: {len(events)}")
event_list = []
for onset, end in events:
    onset_date = pd.Timestamp(tgt_time[onset]).date()
    end_date = pd.Timestamp(tgt_time[end]).date()
    print(f"  {onset_date} to {end_date}")
    event_list.append({
        "onset": str(onset_date),
        "end": str(end_date)
    })

# Write the mask file
# mhw is 1 where the cell is inside a per-cell MHW on that day, 0 otherwise
# Land cells are 0

mhw_mask = per_cell_mhw.astype(np.uint8)

# Create the output directory
os.makedirs('output', exist_ok=True)

# Create xarray dataset for output
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': tgt_time,
        'lat': lat_vals,
        'lon': lon_vals,
    }
)

# Write NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("\nWrote output/mhw_mask.nc")

# Write report
report = {
    "region": {
        "lat_min": 57.83,
        "lat_max": 59.03,
        "lon_min": 17.41,
        "lon_max": 18.61
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2007-06-01",
        "end": "2007-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print(json.dumps(report, indent=2))
