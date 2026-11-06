
import numpy as np
import xarray as xr
import json
import os

# Load saved data
mhw_mask = np.load('/tmp/mhw_mask.npy')  # (92, 60, 60) uint8
tgt_times = np.load('/tmp/tgt_times.npy')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

# Find regional events
n_time = mhw_mask.shape[0]
active = np.array([np.any(mhw_mask[t] > 0) for t in range(n_time)])

events = []
in_event = False
for t in range(n_time):
    if active[t]:
        if not in_event:
            start = t
            in_event = True
    else:
        if in_event:
            events.append((start, t-1))
            in_event = False
if in_event:
    events.append((start, n_time-1))

event_list = []
for (s, e) in events:
    onset = str(tgt_times[s])[:10]
    end_date = str(tgt_times[e])[:10]
    event_list.append({"onset": onset, "end": end_date})

# Create output directory
os.makedirs('output', exist_ok=True)

# Write NetCDF file with dimensions (time, lat, lon)
ds_out = xr.Dataset(
    {
        "mhw": (("time", "lat", "lon"), mhw_mask.astype(np.uint8))
    },
    coords={
        "time": tgt_times,
        "lat": lat_vals,
        "lon": lon_vals,
    }
)

# Add attributes similar to the original dataset
ds_out.attrs['Conventions'] = 'CF-1.4'

ds_out.to_netcdf('output/mhw_mask.nc')
print("Wrote output/mhw_mask.nc")

# Write report.json
report = {
    "region": {
        "lat_min": 54.81,
        "lat_max": 56.01,
        "lon_min": 19.61,
        "lon_max": 20.81
    },
    "baseline_analysed": {
        "start": "1992-01-01",
        "end": "2002-12-31"
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

# Verify the files
print("\nVerifying NetCDF file:")
ds_check = xr.open_dataset('output/mhw_mask.nc')
print(ds_check)
print("mhw dtype:", ds_check['mhw'].dtype)
print("mhw shape:", ds_check['mhw'].shape)
print("mhw unique values:", np.unique(ds_check['mhw'].values))
print("\nTime range:", str(ds_check['time'].values[0])[:10], "to", str(ds_check['time'].values[-1])[:10])
print("Lat range:", ds_check['lat'].values[0], "to", ds_check['lat'].values[-1])
print("Lon range:", ds_check['lon'].values[0], "to", ds_check['lon'].values[-1])

print("\nVerifying report.json:")
with open('output/report.json', 'r') as f:
    report_check = json.load(f)
print(json.dumps(report_check, indent=2))
