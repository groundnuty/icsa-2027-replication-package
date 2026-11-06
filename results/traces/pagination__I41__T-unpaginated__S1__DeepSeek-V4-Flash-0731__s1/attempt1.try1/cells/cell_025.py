
# Final verification of both output files
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print("Variables:", list(ds.variables))
print("Dimensions:", dict(ds.sizes))
print("mhw dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)
print("mhw attrs:", ds['mhw'].attrs)
print("time values count:", len(ds['time'].values))
print("time first:", ds['time'].values[0])
print("time last:", ds['time'].values[-1])
print("lat values count:", len(ds['lat'].values))
print("lat first:", ds['lat'].values[0])
print("lat last:", ds['lat'].values[-1])
print("lon values count:", len(ds['lon'].values))
print("lon first:", ds['lon'].values[0])
print("lon last:", ds['lon'].values[-1])
print("mhw min/max:", int(ds['mhw'].values.min()), int(ds['mhw'].values.max()))
print("mhw zeros:", int((ds['mhw'].values == 0).sum()))
print("mhw ones:", int((ds['mhw'].values == 1).sum()))
ds.close()

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2, sort_keys=True))
