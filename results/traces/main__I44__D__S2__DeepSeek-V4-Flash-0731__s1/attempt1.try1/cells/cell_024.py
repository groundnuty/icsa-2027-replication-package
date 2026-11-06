
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds_check = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc contents:")
print(ds_check)
print(f"\nVariable dtype: {ds_check['mhw'].dtype}")
print(f"Dimensions: {dict(ds_check.sizes)}")
print(f"Time range: {ds_check.time.values[0]} to {ds_check.time.values[-1]}")
print(f"Time count: {len(ds_check.time)}")
print(f"Lat range: {ds_check.lat.values[0]} to {ds_check.lat.values[-1]}")
print(f"Lon range: {ds_check.lon.values[0]} to {ds_check.lon.values[-1]}")
print(f"MHW mask sum: {ds_check['mhw'].sum().values}")
print(f"Unique values: {np.unique(ds_check['mhw'].values)}")

# Verify report.json
with open('/work/output/report.json', 'r') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))

# Verify the report fields are exactly as required
expected_fields = ["region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"]
print(f"\nReport fields: {list(report.keys())}")
assert set(report.keys()) == set(expected_fields), "Report fields mismatch!"

print("\nAll checks passed!")
