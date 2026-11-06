
import os
import json
import xarray as xr
import numpy as np

# Check files exist
print("Output directory contents:", os.listdir('output'))
print("mhw_mask.nc size:", os.path.getsize('output/mhw_mask.nc'))
print("report.json size:", os.path.getsize('output/report.json'))

# Verify report
with open('output/report.json') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))

# Verify report fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present.")

# Verify region
assert report['region'] == {"lat_min": 56.13, "lat_max": 57.33, "lon_min": 17.71, "lon_max": 18.91}
print("Region correct.")

# Verify baseline
assert report['baseline_analysed'] == {"start": "1991-12-27", "end": "2003-01-05"}
print("Baseline correct.")

# Verify target
assert report['target_analysed'] == {"start": "2019-06-01", "end": "2019-08-31"}
print("Target correct.")

# Verify events format
for ev in report['events']:
    assert 'onset' in ev and 'end' in ev
print("Events format correct.")

# Verify complete
assert report['complete'] == True
print("Complete is True.")

# Verify NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nNetCDF:")
print(ds)
print("dtype:", ds.mhw.dtype)
print("shape:", ds.mhw.shape)
assert ds.mhw.dtype == np.uint8
assert len(ds.time) == 92
assert len(ds.lat) == 60
assert len(ds.lon) == 60
print("\nAll checks passed.")
