
import numpy as np
import json
import xarray as xr
import os

# Final comprehensive check
print("=== Final output file check ===")

# Check files exist
for f in ['mhw_mask.nc', 'report.json']:
    path = f'output/{f}'
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"✓ {f} exists ({size} bytes)")
    else:
        print(f"✗ {f} missing!")

# Verify NetCDF
print("\n=== mhw_mask.nc ===")
ds = xr.open_dataset('output/mhw_mask.nc')
print(f"Dimensions: {dict(ds.sizes)}")
print(f"Variables: {list(ds.variables)}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw values: {np.unique(ds['mhw'].values)}")
print(f"mhw sum: {ds['mhw'].sum().values}")
print(f"Time range: {str(ds['time'].values[0])[:10]} to {str(ds['time'].values[-1])[:10]}")
print(f"Number of time steps: {len(ds['time'])}")
print(f"Lat range: {ds['lat'].values[0]:.4f} to {ds['lat'].values[-1]:.4f}")
print(f"Lon range: {ds['lon'].values[0]:.4f} to {ds['lon'].values[-1]:.4f}")
ds.close()

# Verify report
print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"Region: {report['region']}")
print(f"Baseline: {report['baseline_analysed']}")
print(f"Target: {report['target_analysed']}")
print(f"Events: {report['events']}")
print(f"Complete: {report['complete']}")
print(f"Caveats: '{report['caveats']}'")

# Check required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    if field in report:
        print(f"✓ Field '{field}' present")
    else:
        print(f"✗ Field '{field}' MISSING!")

# Verify region values
expected_region = {'lat_min': 59.05, 'lat_max': 60.25, 'lon_min': 21.25, 'lon_max': 22.45}
for key, val in expected_region.items():
    if report['region'][key] == val:
        print(f"✓ Region {key} = {val}")
    else:
        print(f"✗ Region {key} = {report['region'][key]}, expected {val}")

# Verify events are in time order
events = report['events']
for i in range(len(events) - 1):
    if events[i]['onset'] < events[i+1]['onset']:
        print(f"✓ Events in time order")
    else:
        print(f"✗ Events NOT in time order")

print("\n=== All checks passed ===")
