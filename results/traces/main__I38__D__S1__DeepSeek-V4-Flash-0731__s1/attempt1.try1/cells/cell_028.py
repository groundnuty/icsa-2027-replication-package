
# Final verification - let me read back the output files to confirm
import xarray as xr
import json
import numpy as np

# Read mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"  mhw variable: dtype={ds.mhw.dtype}, shape={ds.mhw.shape}")
print(f"  time: {ds.time.values[0]} to {ds.time.values[-1]}, {len(ds.time)} days")
print(f"  lat: {ds.lat.values[0]} to {ds.lat.values[-1]}, {len(ds.lat)} cells")
print(f"  lon: {ds.lon.values[0]} to {ds.lon.values[-1]}, {len(ds.lon)} cells")
print(f"  mhw values: min={ds.mhw.values.min()}, max={ds.mhw.values.max()}, sum={ds.mhw.values.sum()}")

# Read report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))
