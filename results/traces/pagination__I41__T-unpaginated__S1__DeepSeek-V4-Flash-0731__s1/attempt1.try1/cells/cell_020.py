
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print("Dimensions:", dict(ds.sizes))
print("Time count:", len(ds.time))
print("Time first/last:", ds.time.values[0], ds.time.values[-1])
print("Lat:", ds.lat.values[0], "to", ds.lat.values[-1])
print("Lon:", ds.lon.values[0], "to", ds.lon.values[-1])
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("mhw unique:", np.unique(ds.mhw.values))
print("Number of 1s:", int((ds.mhw.values == 1).sum()))
ds.close()

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))

# Check that time dimension has correct dtype
ds2 = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nTime dtype:", ds2.time.dtype)
print("Time values type:", type(ds2.time.values[0]))
ds2.close()
