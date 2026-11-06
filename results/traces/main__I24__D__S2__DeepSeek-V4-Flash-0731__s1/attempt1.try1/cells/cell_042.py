
import xarray as xr
import numpy as np
import json
import os

# Final verification of output files
print("=== Final Verification ===\n")

# Check file existence
print("Files:")
print(f"  output/mhw_mask.nc: {'EXISTS' if os.path.exists('output/mhw_mask.nc') else 'MISSING'}")
print(f"  output/report.json: {'EXISTS' if os.path.exists('output/report.json') else 'MISSING'}")

# Check mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Variable: {list(ds.data_vars.keys())}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw dims: {ds.mhw.dims}")
print(f"  mhw shape: {ds.mhw.shape}")
print(f"  time: {len(ds.time)} values, from {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  lat: {len(ds.lat)} values, from {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  lon: {len(ds.lon)} values, from {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"  mhw unique values: {np.unique(ds.mhw.values)}")
print(f"  mhw sum: {ds.mhw.values.sum()}")

# Check report.json
with open('output/report.json') as f:
    report = json.load(f)

print(f"\nreport.json:")
print(f"  Keys: {list(report.keys())}")
print(f"  Region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: '{report['caveats']}'")

# Verify all required fields are present
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    if field not in report:
        print(f"  MISSING FIELD: {field}")
    else:
        print(f"  Field '{field}' present ✓")

# Verify region bounds
region = report['region']
assert region['lat_min'] == 57.57, f"lat_min wrong: {region['lat_min']}"
assert region['lat_max'] == 58.77, f"lat_max wrong: {region['lat_max']}"
assert region['lon_min'] == 10.25, f"lon_min wrong: {region['lon_min']}"
assert region['lon_max'] == 11.45, f"lon_max wrong: {region['lon_max']}"
print("\nRegion bounds verified ✓")

# Verify target period
assert report['target_analysed'] == {'start': '2004-06-01', 'end': '2004-08-31'}
print("Target period verified ✓")

# Verify events match the MHW mask
mhw_mask = ds.mhw.values
active = mhw_mask.sum(axis=(1, 2)) > 0
active_indices = np.where(active)[0]
events = []
if len(active_indices) > 0:
    start = active_indices[0]
    prev = start
    for idx in active_indices[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            events.append((start, prev))
            start = idx
            prev = idx
    events.append((start, prev))

tt = np.datetime_as_string(ds.time.values, unit='D')
event_list = []
for s, e in events:
    event_list.append({
        "onset": tt[s],
        "end": tt[e]
    })

print(f"\nEvents from MHW mask: {event_list}")
print(f"Events in report: {report['events']}")
assert event_list == report['events'], "Events do not match!"
print("Events match ✓")

print("\n=== All verifications passed ===")
