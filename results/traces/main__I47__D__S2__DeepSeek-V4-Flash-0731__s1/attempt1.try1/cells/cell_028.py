
import os
import json
import xarray as xr
import numpy as np

# Check files exist
print("Files in output/:")
for f in os.listdir('output'):
    print(f"  {f} ({os.path.getsize(os.path.join('output', f))} bytes)")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Variables: {list(ds.data_vars.keys())}")
print(f"  Dims: {dict(ds.sizes)}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw shape: {ds.mhw.shape}")
print(f"  time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nreport.json:")
print(f"  Fields: {list(report.keys())}")
print(f"  Region: {report['region']}")
print(f"  Baseline: {report['baseline_analysed']}")
print(f"  Target: {report['target_analysed']}")
print(f"  Events: {report['events']}")
print(f"  Complete: {report['complete']}")
print(f"  Caveats: '{report['caveats']}'")

# Verify all required fields present
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
assert all(k in report for k in required), "Missing fields in report"
assert all(k in report['region'] for k in ['lat_min', 'lat_max', 'lon_min', 'lon_max']), "Invalid region"
assert all(k in report['baseline_analysed'] for k in ['start', 'end']), "Invalid baseline"
assert all(k in report['target_analysed'] for k in ['start', 'end']), "Invalid target"
for ev in report['events']:
    assert all(k in ev for k in ['onset', 'end']), "Invalid event"

print("\nAll final checks passed!")
