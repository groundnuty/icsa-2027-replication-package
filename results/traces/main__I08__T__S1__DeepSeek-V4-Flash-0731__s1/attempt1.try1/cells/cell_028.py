
import numpy as np
import xarray as xr
import json
import os

# Load saved data
mhw_mask = np.load('/tmp/mhw_mask.npy')  # (92, 60, 60) uint8
tgt_times = np.load('/tmp/tgt_times.npy')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

print("mhw_mask shape:", mhw_mask.shape, "dtype:", mhw_mask.dtype)
print("tgt_times:", tgt_times[0], "to", tgt_times[-1])
print("lat_vals:", lat_vals[0], "to", lat_vals[-1], "n =", len(lat_vals))
print("lon_vals:", lon_vals[0], "to", lon_vals[-1], "n =", len(lon_vals))

# Find regional events
n_time = mhw_mask.shape[0]
active = np.zeros(n_time, dtype=bool)
for t in range(n_time):
    active[t] = np.any(mhw_mask[t, :, :] > 0)

events = []
in_event = False
for t in range(n_time):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t-1))
            in_event = False
if in_event:
    events.append((event_start, n_time-1))

print(f"Regional events: {len(events)}")
event_list = []
for (start, end) in events:
    onset = str(tgt_times[start])[:10]
    end_date = str(tgt_times[end])[:10]
    event_list.append({"onset": onset, "end": end_date})
    print(f"  Event: {onset} to {end_date}")

# Create output directory
os.makedirs('output', exist_ok=True)

# Write NetCDF file
# mhw_mask has dimensions (time, lat, lon)
# Use time, latitude, longitude from the original dataset

ds_out = xr.Dataset(
    {
        "mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))
    },
    coords={
        "time": tgt_times,
        "latitude": lat_vals,
        "longitude": lon_vals,
    }
)

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

# Verify the files
print("\nVerifying NetCDF file:")
ds_check = xr.open_dataset('output/mhw_mask.nc')
print(ds_check)
print("mhw dtype:", ds_check['mhw'].dtype)
print("mhw shape:", ds_check['mhw'].shape)
print("mhw values:", np.unique(ds_check['mhw'].values))

print("\nVerifying report.json:")
with open('output/report.json', 'r') as f:
    report_check = json.load(f)
print(json.dumps(report_check, indent=2))
