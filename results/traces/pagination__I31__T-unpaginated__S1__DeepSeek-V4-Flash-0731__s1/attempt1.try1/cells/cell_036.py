
import json
import numpy as np
import xarray as xr
import os

# Verify output files exist
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc missing"
assert os.path.exists('output/report.json'), "report.json missing"

# Read mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc verification ===")
print(f"Variable: mhw")
print(f"Shape: {ds.mhw.shape}")
print(f"Dtype: {ds.mhw.dtype}")
print(f"Unique values: {np.unique(ds.mhw.values)}")
print(f"Sum: {int(ds.mhw.values.sum())}")
print(f"Time: {len(ds.time)} values, {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Lat: {len(ds.lat)} values, {ds.lat.values[0]:.4f} to {ds.lat.values[-1]:.4f}")
print(f"Lon: {len(ds.lon)} values, {ds.lon.values[0]:.4f} to {ds.lon.values[-1]:.4f}")

# Verify time covers all target days
expected_dates = np.array([
    np.datetime64(f'2017-{m:02d}-{d:02d}')
    for m, d in [(6, d) for d in range(1, 31)] + [(7, d) for d in range(1, 32)] + [(8, d) for d in range(1, 32)]
])
assert len(ds.time) == 92, f"Expected 92 time steps, got {len(ds.time)}"
print(f"All 92 target days covered: {np.array_equal(ds.time.values, expected_dates)}")

# Read report.json
with open('output/report.json') as f:
    report = json.load(f)

print("\n=== report.json verification ===")
print(json.dumps(report, indent=2))

# Verify all required fields
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    assert field in report, f"Missing field: {field}"
print(f"\nAll required fields present: True")

# Verify types
assert isinstance(report['region'], dict)
assert isinstance(report['baseline_analysed'], dict) or report['baseline_analysed'] is None
assert isinstance(report['target_analysed'], dict) or report['target_analysed'] is None
assert isinstance(report['events'], list)
assert isinstance(report['complete'], bool)
assert isinstance(report['caveats'], str)
print(f"Field types correct: True")

print("\nAll verifications passed!")
