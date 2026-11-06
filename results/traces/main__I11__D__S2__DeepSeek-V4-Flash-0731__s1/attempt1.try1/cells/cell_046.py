
import numpy as np
import xarray as xr
import json
import os

print("=== Final Output Files ===")
for f in os.listdir('output'):
    path = os.path.join('output', f)
    print(f"  {f}: {os.path.getsize(path)} bytes")

print("\n=== mhw_mask.nc Verification ===")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
assert dict(ds.sizes) == {'time': 92, 'lat': 60, 'lon': 60}, "Wrong dimensions"
assert ds.mhw.dtype == np.uint8, "Wrong dtype"
assert set(np.unique(ds.mhw.values).tolist()) == {0, 1}, "Values should be 0/1"
print("  ✓ Dimensions, dtype, values correct")
print(f"  ✓ Time: {str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]}")
print(f"  ✓ Lat: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  ✓ Lon: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"  ✓ Total MHW cells: {ds.mhw.values.sum()}")

print("\n=== report.json Verification ===")
with open('output/report.json') as f:
    report = json.load(f)

required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("  ✓ All required fields present")

assert report['region'] == {'lat_min': 55.67, 'lat_max': 56.87, 'lon_min': 16.45, 'lon_max': 17.65}
assert report['baseline_analysed'] == {'start': '1991-12-27', 'end': '2003-01-05'}
assert report['target_analysed'] == {'start': '2021-06-01', 'end': '2021-08-31'}
assert report['complete'] == True
print("  ✓ Region, baseline, target, complete fields correct")

print(f"  ✓ Events: {report['events']}")
for ev in report['events']:
    assert 'onset' in ev and 'end' in ev
print("  ✓ Events have onset and end")

print("\n=== All checks passed ===")
