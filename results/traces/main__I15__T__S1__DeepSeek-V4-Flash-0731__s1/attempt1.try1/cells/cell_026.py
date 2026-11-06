import xarray as xr
import numpy as np
import json
import os

# Final verification of output files
print("=== Output files ===")
for root, dirs, files in os.walk('output'):
    for file in files:
        path = os.path.join(root, file)
        print(f"  {path}: {os.path.getsize(path)} bytes")

# Verify mhw_mask.nc
print("\n=== mhw_mask.nc ===")
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds_out)
print(f"\nmhw dtype: {ds_out['mhw'].dtype}")
print(f"mhw shape: {ds_out['mhw'].shape}")
print(f"mhw values: {np.unique(ds_out['mhw'].values)}")
print(f"mhw sum: {ds_out['mhw'].values.sum()}")
print(f"Time: {len(ds_out['time'])} days")
print(f"Lat: {len(ds_out['lat'])} values, {ds_out['lat'].values[0]} to {ds_out['lat'].values[-1]}")
print(f"Lon: {len(ds_out['lon'])} values, {ds_out['lon'].values[0]} to {ds_out['lon'].values[-1]}")

# Verify report.json
print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Check that the fields are exactly as required
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    if field not in report:
        print(f"MISSING FIELD: {field}")
    else:
        print(f"Field '{field}': present ✓")

# Check region
expected_region = {"lat_min": 56.13, "lat_max": 57.33, "lon_min": 17.71, "lon_max": 18.91}
print(f"\nRegion matches: {report['region'] == expected_region}")

# Check events format
for ev in report['events']:
    assert 'onset' in ev and 'end' in ev
    print(f"Event: {ev['onset']} to {ev['end']}")

# Check complete
print(f"\nComplete: {report['complete']}")
print(f"Caveats: '{report['caveats']}'")
