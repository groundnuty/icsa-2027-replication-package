
import numpy as np
import datetime
import json
import os

# Load data
mhw_mask = np.load('mhw_mask_per_cell.npy')  # (92, 60, 60) uint8
lat_vals = np.load('lat_vals.npy')
lon_vals = np.load('lon_vals.npy')
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

# The mhw_mask is (92, 60, 60) with 1 for cells inside per-cell MHWs, 0 otherwise
# For the output NetCDF, I need dimensions (time, lat, lon)
# The mask already includes 0 for land cells (since we only set 1 for sea cells in MHWs)

# Determine regional events
active = mhw_mask.sum(axis=(1, 2)) > 0
events = []
i = 0
while i < len(active):
    if active[i]:
        start = i
        while i < len(active) and active[i]:
            i += 1
        end = i - 1
        events.append({
            'onset': target_dt[start].strftime('%Y-%m-%d'),
            'end': target_dt[end].strftime('%Y-%m-%d')
        })
    else:
        i += 1

print("Regional events:")
for e in events:
    print(f"  {e['onset']} to {e['end']}")

# Write output files
os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc
import xarray as xr

# Create time coordinate values (as datetime64)
time_vals = np.array([np.datetime64(dt) for dt in target_dt], dtype='datetime64[ns]')

# Create the dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_vals,
        'lat': lat_vals,
        'lon': lon_vals
    }
)
ds_out['mhw'].attrs['long_name'] = 'Marine heatwave mask'
ds_out['mhw'].attrs['units'] = '1 = inside per-cell MHW, 0 = not'
ds_out['mhw'].attrs['description'] = '1 where the cell is inside a per-cell MHW on that day, 0 otherwise (land cells are 0)'

ds_out.to_netcdf('output/mhw_mask.nc')
print("Wrote output/mhw_mask.nc")

# Write report.json
report = {
    'region': {
        'lat_min': 54.17,
        'lat_max': 55.37,
        'lon_min': 13.25,
        'lon_max': 14.45
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2014-06-01',
        'end': '2014-08-31'
    },
    'events': events,
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print("\nReport:")
print(json.dumps(report, indent=2))
