
import os
import xarray as xr
import json

# List output directory
print("Output directory contents:")
for f in os.listdir('output'):
    path = os.path.join('output', f)
    size = os.path.getsize(path)
    print(f"  {f}: {size} bytes")

# Final verification of mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  Variables: {list(ds.data_vars.keys())}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw shape: {ds.mhw.shape}")
print(f"  mhw values: min={ds.mhw.values.min()}, max={ds.mhw.values.max()}")
print(f"  mhw sum: {ds.mhw.values.sum()}")

# Final verification of report.json
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nreport.json:")
print(json.dumps(report, indent=2))

# Verify all fields match requirements
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    assert field in report, f"Missing field: {field}"
    print(f"  ✓ {field}")

assert report['complete'] == True
assert isinstance(report['caveats'], str)
assert isinstance(report['events'], list)
assert report['region']['lat_min'] == 54.45
assert report['region']['lat_max'] == 55.65
assert report['region']['lon_min'] == 16.05
assert report['region']['lon_max'] == 17.25

print("\nAll checks passed!")
