import xarray as xr
import json
import numpy as np

# Verify the NetCDF file
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== NetCDF File ===")
print(ds)
print(f"\nmhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw values: {np.unique(ds['mhw'].values)}")
print(f"mhw sum: {ds['mhw'].values.sum()}")
print(f"time: {ds['time'].values[:5]} ... {ds['time'].values[-5:]}")
print(f"lat: {ds['lat'].values[:3]} ... {ds['lat'].values[-3:]}")
print(f"lon: {ds['lon'].values[:3]} ... {ds['lon'].values[-3:]}")
ds.close()

# Verify the report
print("\n=== Report ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Verify the report has exactly the required fields
required_fields = ["region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"]
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present in report.")

# Check no extra fields
for field in report:
    assert field in required_fields, f"Extra field: {field}"
print("No extra fields in report.")
