
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print("Dimensions:", dict(ds.dims))
print("Time:", ds.time.values)
print("Lat range:", ds.lat.values[0], "to", ds.lat.values[-1], "count:", len(ds.lat.values))
print("Lon range:", ds.lon.values[0], "to", ds.lon.values[-1], "count:", len(ds.lon.values))
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("mhw values range:", ds.mhw.values.min(), "to", ds.mhw.values.max())
print("mhw unique values:", np.unique(ds.mhw.values))
print("Number of 1s:", (ds.mhw.values == 1).sum())
print("Number of 0s:", (ds.mhw.values == 0).sum())
ds.close()

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))
