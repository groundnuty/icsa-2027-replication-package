
# Final comprehensive verification
import json
import xarray as xr
import os

# Check files exist
print("Files in output/:")
for f in os.listdir('output'):
    print(f"  {f} ({os.path.getsize(os.path.join('output', f))} bytes)")

# Read report
with open('output/report.json') as f:
    report = json.load(f)

print("\nReport:")
print(json.dumps(report, indent=2))

# Check required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\n✓ All required fields present")

# Check region
assert report['region'] == {"lat_min": 54.13, "lat_max": 55.33, "lon_min": 14.67, "lon_max": 15.87}
print("✓ Region correct")

# Check baseline
assert report['baseline_analysed'] == {"start": "1991-12-27", "end": "2003-01-05"}
print("✓ Baseline analysed correct")

# Check target
assert report['target_analysed'] == {"start": "2008-06-01", "end": "2008-08-31"}
print("✓ Target analysed correct")

# Check complete
assert report['complete'] == True
print("✓ Complete flag correct")

# Check caveats is string
assert isinstance(report['caveats'], str)
print("✓ Caveats is string")

# Check events format
for event in report['events']:
    assert 'onset' in event and 'end' in event
    assert isinstance(event['onset'], str) and isinstance(event['end'], str)
print(f"✓ Events format correct ({len(report['events'])} events)")

# Read NC file
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\n=== mhw_mask.nc ===")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  Variable 'mhw' dtype: {ds.mhw.dtype}")
print(f"  Variable 'mhw' shape: {ds.mhw.shape}")
print(f"  mhw values: {ds.mhw.values.min()} to {ds.mhw.values.max()}")
assert ds.mhw.dtype == 'uint8'
assert ds.mhw.shape == (92, 60, 60)
print("✓ NC file structure correct")

print("\nAll verifications passed!")
