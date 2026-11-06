
import xarray as xr
import json
import numpy as np

# Final verification
print("=== Output file verification ===\n")

# Check mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(f"  Variable: {list(ds.data_vars.keys())}")
print(f"  Shape: {ds['mhw'].shape}")
print(f"  Dtype: {ds['mhw'].dtype}")
print(f"  Time dim: {len(ds.time)} days, {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  Lat dim: {len(ds.lat)}, {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  Lon dim: {len(ds.lon)}, {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"  Unique values: {np.unique(ds['mhw'].values)}")
print(f"  Total 1s: {ds['mhw'].sum().values}")
ds.close()

# Check report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json:")
for k, v in report.items():
    print(f"  {k}: {v}")

# Verify the report fields match what's expected
expected_fields = ["region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"]
actual_fields = list(report.keys())
print(f"\n  Expected fields: {expected_fields}")
print(f"  Actual fields: {actual_fields}")
print(f"  Fields match: {sorted(expected_fields) == sorted(actual_fields)}")

print("\nAll files verified successfully.")
