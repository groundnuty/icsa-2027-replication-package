
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"Dimensions: {dict(ds_out.sizes)}")
print(f"Variable: mhw, dtype={ds_out['mhw'].dtype}")
print(f"mhw range: {ds_out['mhw'].min().values} to {ds_out['mhw'].max().values}")
print(f"Time: {ds_out.time.values[0]} to {ds_out.time.values[-1]}")
print(f"Lat: {ds_out.lat.values[0]} to {ds_out.lat.values[-1]}, count={len(ds_out.lat.values)}")
print(f"Lon: {ds_out.lon.values[0]} to {ds_out.lon.values[-1]}, count={len(ds_out.lon.values)}")
print(f"All zeros: {np.all(ds_out['mhw'].values == 0)}")

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))

# Verify all required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    if field not in report:
        print(f"MISSING FIELD: {field}")
    else:
        print(f"Field '{field}': present")

# Verify events structure
if isinstance(report['events'], list):
    print(f"Events: list with {len(report['events'])} items")
    for e in report['events']:
        print(f"  {e}")
else:
    print("ERROR: events is not a list")
