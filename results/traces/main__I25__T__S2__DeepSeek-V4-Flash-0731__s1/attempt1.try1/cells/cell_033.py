
import xarray as xr
import json
import numpy as np

# Read back mhw_mask.nc
with xr.open_dataset('output/mhw_mask.nc') as ds:
    print("=== mhw_mask.nc ===")
    print(f"  Shape: {ds['mhw'].shape}")
    print(f"  Dtype: {ds['mhw'].dtype}")
    print(f"  Time: {ds.time.values[0]} to {ds.time.values[-1]}")
    print(f"  Lat: {ds.lat.values[0]} to {ds.lat.values[-1]}")
    print(f"  Lon: {ds.lon.values[0]} to {ds.lon.values[-1]}")
    print(f"  mhw sum: {ds['mhw'].sum().values}")
    print(f"  Unique values: {np.unique(ds['mhw'].values)}")

# Read back report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
    print("\n=== report.json ===")
    print(json.dumps(report, indent=2))

# Verify report fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present")

# Check region bounds
assert report['region']['lat_min'] == 57.57
assert report['region']['lat_max'] == 58.77
assert report['region']['lon_min'] == 10.25
assert report['region']['lon_max'] == 11.45
print("Region bounds correct")

# Check event format
for event in report['events']:
    assert 'onset' in event and 'end' in event
    print(f"  Event: {event['onset']} to {event['end']}")
