
import xarray as xr
import json
import numpy as np

# Final verification
print("=== Final Verification ===")

# Check mhw_mask.nc
with xr.open_dataset('output/mhw_mask.nc') as ds:
    print("\nmhw_mask.nc:")
    print(f"  Variable 'mhw': {ds['mhw'].dtype}, shape {ds['mhw'].shape}")
    print(f"  Dimensions: {list(ds.dims)}")
    print(f"  Time range: {ds.time.values[0]} to {ds.time.values[-1]} ({len(ds.time.values)} days)")
    print(f"  Lat range: {ds.lat.values[0]:.4f} to {ds.lat.values[-1]:.4f}")
    print(f"  Lon range: {ds.lon.values[0]:.4f} to {ds.lon.values[-1]:.4f}")
    print(f"  Sum: {ds['mhw'].sum().values}")
    print(f"  Unique values: {np.unique(ds['mhw'].values)}")

# Check report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
    print("\nreport.json:")
    print(json.dumps(report, indent=2))

# Verify all required fields
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present in report.json ✓")

# Verify events are in time order
for i in range(len(report['events']) - 1):
    assert report['events'][i]['end'] < report['events'][i+1]['onset']
print("Events are in time order ✓")

# Verify region bounds
assert report['region'] == {"lat_min": 57.57, "lat_max": 58.77, "lon_min": 10.25, "lon_max": 11.45}
print("Region bounds correct ✓")

# Verify baseline_analysed
print(f"baseline_analysed: {report['baseline_analysed']}")
print(f"target_analysed: {report['target_analysed']}")

# Verify events
print(f"Events: {len(report['events'])}")
for e in report['events']:
    print(f"  {e['onset']} to {e['end']}")

print("\n=== All checks passed ===")
