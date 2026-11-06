
import json
import xarray as xr
import numpy as np

# Final verification
print("=== Final Verification ===")

# Check report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("report.json:")
print(json.dumps(report, indent=2))

# Check mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nmhw_mask.nc:")
print("Dimensions:", dict(ds.sizes))
print("dtype:", ds.mhw.dtype)
print("Shape:", ds.mhw.shape)
print("Coord values:")
print("  time:", ds.time.values[0], "...", ds.time.values[-1])
print("  lat:", ds.lat.values[0], "...", ds.lat.values[-1])
print("  lon:", ds.lon.values[0], "...", ds.lon.values[-1])
print("mhw values:", np.unique(ds.mhw.values))

# Verify events match
active = ds.mhw.values.sum(axis=(1,2)) > 0
print("\nActive days count:", active.sum())
print("Events in report:", report['events'])
