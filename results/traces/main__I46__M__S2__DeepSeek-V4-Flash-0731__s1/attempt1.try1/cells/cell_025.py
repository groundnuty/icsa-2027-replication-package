
import xarray as xr
import json
import numpy as np

# Re-read and verify both files
print("=== mhw_mask.nc ===")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print()
print("mhw dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)
print("mhw min/max:", ds['mhw'].values.min(), ds['mhw'].values.max())
print("mhw sum:", int(ds['mhw'].values.sum()))
print()

print("=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))
print()

# Verify all required fields are present
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    assert field in report, f"Missing field: {field}"
print("All required fields present in report.json")
