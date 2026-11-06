
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(ds)
print(f"\nmhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw min: {ds['mhw'].min().values}, max: {ds['mhw'].max().values}")
print(f"time: {ds.time.values[0]} to {ds.time.values[-1]}, count: {len(ds.time)}")
print(f"lat: {ds.lat.values[0]} to {ds.lat.values[-1]}, count: {len(ds.lat)}")
print(f"lon: {ds.lon.values[0]} to {ds.lon.values[-1]}, count: {len(ds.lon)}")

# Verify report.json
print("\n=== report.json ===")
with open('output/report.json') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Verify all required fields are present
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present in report")

# Verify region
assert report['region'] == {'lat_min': 54.17, 'lat_max': 55.37, 'lon_min': 13.25, 'lon_max': 14.45}
print("Region correct")

# Verify baseline_analysed
assert report['baseline_analysed'] == {'start': '1991-12-27', 'end': '2003-01-05'}
print("Baseline correct")

# Verify target_analysed
assert report['target_analysed'] == {'start': '2014-06-01', 'end': '2014-08-31'}
print("Target correct")

# Verify events format
for ev in report['events']:
    assert set(ev.keys()) == {'onset', 'end'}
    assert 'onset' in ev and 'end' in ev
print("Events format correct")

# Verify complete
assert report['complete'] == True
print("Complete flag correct")

print("\nAll checks passed!")
