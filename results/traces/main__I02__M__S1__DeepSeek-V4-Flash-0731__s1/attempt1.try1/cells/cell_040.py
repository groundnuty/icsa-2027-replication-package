
import xarray as xr
import numpy as np
import json

# Final verification of mhw_mask.nc
print("=== mhw_mask.nc ===")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"Dimensions: {dict(ds.dims)}")
print(f"Variables: {list(ds.data_vars)}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw min/max: {ds['mhw'].min().values}, {ds['mhw'].max().values}")
print(f"time range: {str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]}")
print(f"lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")
ds.close()

print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Verify all required fields are present and have correct types
assert 'region' in report
assert 'lat_min' in report['region'] and isinstance(report['region']['lat_min'], (int, float))
assert 'lat_max' in report['region'] and isinstance(report['region']['lat_max'], (int, float))
assert 'lon_min' in report['region'] and isinstance(report['region']['lon_min'], (int, float))
assert 'lon_max' in report['region'] and isinstance(report['region']['lon_max'], (int, float))
assert 'baseline_analysed' in report
assert 'start' in report['baseline_analysed'] and isinstance(report['baseline_analysed']['start'], str)
assert 'end' in report['baseline_analysed'] and isinstance(report['baseline_analysed']['end'], str)
assert 'target_analysed' in report
assert 'start' in report['target_analysed'] and isinstance(report['target_analysed']['start'], str)
assert 'end' in report['target_analysed'] and isinstance(report['target_analysed']['end'], str)
assert 'events' in report and isinstance(report['events'], list)
assert 'complete' in report and isinstance(report['complete'], bool)
assert 'caveats' in report and isinstance(report['caveats'], str)

print("\nAll checks passed!")
