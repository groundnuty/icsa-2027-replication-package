
import xarray as xr
import json
import numpy as np
from datetime import date, timedelta

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"Dimensions: {ds.sizes}")
print(f"Variables: {list(ds.data_vars)}")
print(f"mhw dtype: {ds.mhw.dtype}")
print(f"mhw shape: {ds.mhw.shape}")
print(f"mhw values: min={ds.mhw.min().values}, max={ds.mhw.max().values}, sum={ds.mhw.sum().values}")
print(f"time: {ds.time.values[0]} to {ds.time.values[-1]}, count={len(ds.time)}")
print(f"lat: {ds.lat.values[0]} to {ds.lat.values[-1]}, count={len(ds.lat)}")
print(f"lon: {ds.lon.values[0]} to {ds.lon.values[-1]}, count={len(ds.lon)}")

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))

# Check required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for f in required_fields:
    assert f in report, f"Missing required field: {f}"
print("\nAll required fields present.")

# Verify region
region = report['region']
for k in ['lat_min', 'lat_max', 'lon_min', 'lon_max']:
    assert k in region, f"Missing region field: {k}"
print(f"Region: lat {region['lat_min']}-{region['lat_max']}, lon {region['lon_min']}-{region['lon_max']}")

# Verify events format
for e in report['events']:
    assert 'onset' in e and 'end' in e, f"Event missing onset/end: {e}"
print(f"Events: {len(report['events'])}")

# Verify baseline_analysed
ba = report['baseline_analysed']
assert 'start' in ba and 'end' in ba
print(f"Baseline analysed: {ba['start']} to {ba['end']}")

# Verify target_analysed
ta = report['target_analysed']
assert 'start' in ta and 'end' in ta
print(f"Target analysed: {ta['start']} to {ta['end']}")

# Verify complete is boolean
assert isinstance(report['complete'], bool)
assert report['complete'] == True
print(f"Complete: {report['complete']}")

# Verify caveats is string
assert isinstance(report['caveats'], str)
print(f"Caveats: '{report['caveats']}'")
ds.close()

print("\n=== ALL CHECKS PASSED ===")
