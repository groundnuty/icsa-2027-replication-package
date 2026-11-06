
import xarray as xr
import json
import numpy as np

# ===== Final verification =====

# 1. Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  Variables: {list(ds.data_vars)}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw shape: {ds.mhw.shape}")
print(f"  mhw unique values: {np.unique(ds.mhw.values)}")
print(f"  mhw sum (active cell-days): {int(ds.mhw.sum().values)}")
print(f"  time: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  lat: {ds.lat.values[0]} to {ds.lat.values[-1]}, n={len(ds.lat)}")
print(f"  lon: {ds.lon.values[0]} to {ds.lon.values[-1]}, n={len(ds.lon)}")
print(f"  Lat step: {ds.lat.values[1] - ds.lat.values[0]}")
print(f"  Lon step: {ds.lon.values[1] - ds.lon.values[0]}")
ds.close()

# 2. Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))

# 3. Cross-check that all required fields are present and correct
assert 'region' in report
assert 'baseline_analysed' in report
assert 'target_analysed' in report
assert 'events' in report
assert 'complete' in report
assert 'caveats' in report

assert report['complete'] == True
assert isinstance(report['caveats'], str)

# Check region bounds match the task specification
assert report['region']['lat_min'] == 60.49
assert report['region']['lat_max'] == 61.69
assert report['region']['lon_min'] == 17.25
assert report['region']['lon_max'] == 18.45

# Check baseline_analysed
assert report['baseline_analysed']['start'] == '1991-12-27'
assert report['baseline_analysed']['end'] == '2003-01-05'

# Check target_analysed
assert report['target_analysed']['start'] == '2003-06-01'
assert report['target_analysed']['end'] == '2003-08-31'

# Check events format
for e in report['events']:
    assert 'onset' in e and 'end' in e
    assert isinstance(e['onset'], str) and isinstance(e['end'], str)

print("\n=== ALL FINAL CHECKS PASSED ===")
