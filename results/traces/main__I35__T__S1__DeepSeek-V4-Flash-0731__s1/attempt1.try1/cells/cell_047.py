
import numpy as np
import xarray as xr
import json
import os

# Load the float64-computed MHW mask
mhw_mask = np.load('/tmp/mhw_mask_f64.npy')  # (92, 60, 60) uint8

# Load region coordinates and target times
region_lat = np.load('/tmp/region_lat.npy')
region_lon = np.load('/tmp/region_lon.npy')
target_times_full = np.load('/tmp/target_times_full.npy')

# Load target dates for report
target_times = np.load('/tmp/target_times.npy')
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

print(f"mhw_mask shape: {mhw_mask.shape}, dtype: {mhw_mask.dtype}")
print(f"region_lat: {len(region_lat)} values, {region_lat[0]} to {region_lat[-1]}")
print(f"region_lon: {len(region_lon)} values, {region_lon[0]} to {region_lon[-1]}")
print(f"target_times_full: {len(target_times_full)} values")
print(f"  First: {target_times_full[0]}, Last: {target_times_full[-1]}")

# Create output directory
os.makedirs('output', exist_ok=True)

# Create xarray Dataset for output
mhw_data = mhw_mask.astype(np.uint8)

out_ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_data)
    },
    coords={
        'time': target_times_full,
        'lat': region_lat,
        'lon': region_lon
    }
)
out_ds['mhw'].attrs['long_name'] = 'Marine heatwave mask (1 if inside per-cell MHW)'
out_ds['mhw'].attrs['units'] = '1'
out_ds['mhw'].attrs['description'] = '1 if the cell is inside a per-cell MHW on that day, 0 otherwise'

# Write NetCDF
out_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written output/mhw_mask.nc")

# Regional events
active = mhw_mask.sum(axis=(1, 2)) > 0
events = []
start = None
for t in range(len(active)):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t-1))
            start = None
if start is not None:
    events.append((start, len(active)-1))

event_list = []
for s, e in events:
    onset = str(target_dates[s])
    end = str(target_dates[e])
    event_list.append({"onset": onset, "end": end})

print(f"Regional events: {event_list}")

report = {
    "region": {
        "lat_min": 59.93,
        "lat_max": 61.13,
        "lon_min": 18.69,
        "lon_max": 19.89
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2009-06-01",
        "end": "2009-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Written output/report.json")
