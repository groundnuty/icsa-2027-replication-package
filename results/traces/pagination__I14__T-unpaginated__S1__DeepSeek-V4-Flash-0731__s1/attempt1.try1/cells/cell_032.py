
import xarray as xr
import numpy as np

# Check output file
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== Output mhw_mask.nc ===")
print(ds)
print(f"\nmhw dtype: {ds.mhw.dtype}")
print(f"mhw shape: {ds.mhw.shape}")

# Check the time dimension is correct
print(f"\ntime values: {ds.time.values}")
print(f"time count: {len(ds.time)}")

# Check the report
import json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\n=== Report ===")
print(json.dumps(report, indent=2))

# Verify all required fields exist
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for key in required:
    assert key in report, f"Missing field: {key}"
print("\nAll required report fields present. ✓")

# Verify region fields
assert 'lat_min' in report['region'] and 'lat_max' in report['region']
assert 'lon_min' in report['region'] and 'lon_max' in report['region']
print("Region fields correct. ✓")

# Verify events format
for event in report['events']:
    assert 'onset' in event and 'end' in event
print("Events format correct. ✓")

ds.close()
print("\nAll checks passed.")
