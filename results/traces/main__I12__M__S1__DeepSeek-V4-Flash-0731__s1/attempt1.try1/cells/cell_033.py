
import xarray as xr
import numpy as np
import json

# Read back the netCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"Dimensions: {dict(ds.dims)}")
print(f"Variable mhw: dtype={ds.mhw.dtype}, shape={ds.mhw.shape}")
print(f"time: {ds.time.values[0]} to {ds.time.values[-1]} ({len(ds.time)} entries)")
print(f"lat: {ds.lat.values[0]} to {ds.lat.values[-1]} ({len(ds.lat)} entries)")
print(f"lon: {ds.lon.values[0]} to {ds.lon.values[-1]} ({len(ds.lon)} entries)")
print(f"mhw values: min={ds.mhw.values.min()}, max={ds.mhw.values.max()}, sum={ds.mhw.values.sum()}")
print(f"Unique values: {np.unique(ds.mhw.values)}")
ds.close()

print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Verify report fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present in report.json")
