
import numpy as np
import datetime
import json
import xarray as xr
import os

# Load data
target_times = np.load('/tmp/target_times.npy')
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]
mhw_mask = np.load('/tmp/mhw_mask.npy')  # (92, 60, 60)

# Get region coordinates
import fsspec
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 59.93) & (lat <= 61.13))[0]
lon_idx = np.where((lon >= 18.69) & (lon <= 19.89))[0]
region_lat = lat[lat_idx]
region_lon = lon[lon_idx]
times = ds.time.values
dt_times = np.array([np.datetime64(t) for t in times])
tg_start = np.searchsorted(dt_times, np.datetime64('2009-06-01'))
tg_end = np.searchsorted(dt_times, np.datetime64('2009-08-31'), side='right') - 1
target_times_full = times[tg_start:tg_end+1]

# Verify mhw_mask shape matches
print(f"mhw_mask shape: {mhw_mask.shape}")
print(f"region_lat: {len(region_lat)}, region_lon: {len(region_lon)}, target times: {len(target_times_full)}")

# Create output directory
os.makedirs('output', exist_ok=True)

# Create xarray Dataset for output
mhw_data = mhw_mask.astype(np.uint8)
# mhw_data shape: (92, 60, 60)

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

# Write NetCDF
out_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written output/mhw_mask.nc")

# Now create report.json
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
print(f"Events: {event_list}")
