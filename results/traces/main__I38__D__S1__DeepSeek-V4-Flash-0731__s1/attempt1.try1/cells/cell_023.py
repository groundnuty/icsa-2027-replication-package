
import xarray as xr
import json
import os

# Verify mhw_mask.nc
print("=== mhw_mask.nc ===")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("time:", ds.time.values[0], "to", ds.time.values[-1])
print("lat:", ds.lat.values[0], "to", ds.lat.values[-1])
print("lon:", ds.lon.values[0], "to", ds.lon.values[-1])
print("mhw values:", ds.mhw.values.min(), "to", ds.mhw.values.max())

# Verify report.json
print("\n=== report.json ===")
with open('output/report.json') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Check file sizes
print("\n=== File sizes ===")
print("mhw_mask.nc:", os.path.getsize('output/mhw_mask.nc'), "bytes")
print("report.json:", os.path.getsize('output/report.json'), "bytes")
