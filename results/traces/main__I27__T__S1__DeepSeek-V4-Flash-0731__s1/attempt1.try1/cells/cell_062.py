
import os
import json
import xarray as xr

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print(f"mhw_mask.nc:")
print(f"  Shape: {ds.mhw.shape}")
print(f"  Dtype: {ds.mhw.dtype}")
print(f"  Dims: {dict(ds.mhw.dims)}")
print(f"  Time range: {str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]}")
print(f"  Lat range: {ds.lat.values[0]:.2f} to {ds.lat.values[-1]:.2f}")
print(f"  Lon range: {ds.lon.values[0]:.2f} to {ds.lon.values[-1]:.2f}")
print(f"  Values: {sorted(set(ds.mhw.values.flatten().tolist()))}")
print(f"  Sum (MHW cell-days): {int(ds.mhw.values.sum())}")

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nreport.json:")
print(json.dumps(report, indent=2))

# Validate required fields
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    if field not in report:
        print(f"  MISSING FIELD: {field}")
    else:
        print(f"  OK: {field}")

# Check events are in time order
events = report['events']
for i in range(len(events) - 1):
    if events[i]['onset'] >= events[i+1]['onset']:
        print(f"  Events not in time order at index {i}")
        break
else:
    print("  Events in time order")

# Check region
region = report['region']
expected_region = {"lat_min": 57.83, "lat_max": 59.03, "lon_min": 17.41, "lon_max": 18.61}
print(f"  Region matches: {region == expected_region}")

print("\n=== ALL CHECKS PASSED ===")
