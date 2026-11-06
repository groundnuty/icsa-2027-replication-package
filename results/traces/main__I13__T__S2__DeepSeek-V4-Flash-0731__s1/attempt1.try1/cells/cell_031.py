
import numpy as np
import xarray as xr
import json

# Verify output files
print("=== Verifying mhw_mask.nc ===")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print(f"mhw dtype: {ds.mhw.dtype}")
print(f"mhw shape: {ds.mhw.shape}")
print(f"mhw sum: {ds.mhw.sum().item()}")
print(f"mhw unique values: {np.unique(ds.mhw.values)}")
print(f"time values: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"lat values: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"lon values: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print()

print("=== Verifying report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))
