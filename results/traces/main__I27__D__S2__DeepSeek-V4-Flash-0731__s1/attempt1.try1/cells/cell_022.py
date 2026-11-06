
import json
import xarray as xr
import numpy as np

# Verify output files
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("Report:")
print(json.dumps(report, indent=2))

print("\nNetCDF:")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("Unique values:", np.unique(ds.mhw.values))
print("mhw sum:", ds.mhw.values.sum())
print("Time range:", ds.time.values[0], "to", ds.time.values[-1])
print("Lat range:", ds.lat.values[0], "to", ds.lat.values[-1])
print("Lon range:", ds.lon.values[0], "to", ds.lon.values[-1])
