
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"Dimensions: {dict(ds.sizes)}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"Time range: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"Lat range: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"Lon range: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")
print(f"Sum of mhw: {ds['mhw'].sum().values}")

# Verify report.json
with open('/work/output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))

# Verify all required fields present
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present.")

# Verify region bounds
assert report['region'] == {"lat_min": 56.13, "lat_max": 57.33, "lon_min": 17.71, "lon_max": 18.91}
print("Region bounds correct.")

# Verify events are in time order
events = report['events']
for i in range(len(events)-1):
    assert events[i]['onset'] <= events[i+1]['onset']
print("Events in time order.")

print("\nAll checks passed.")
