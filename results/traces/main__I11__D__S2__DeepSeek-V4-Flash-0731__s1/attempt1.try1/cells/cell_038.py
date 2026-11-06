
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print("Dims:", dict(ds.sizes))
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("mhw sum:", ds.mhw.values.sum())
print("mhw unique:", np.unique(ds.mhw.values))
print("Time:", ds.time.values[0], "to", ds.time.values[-1])
print("Lat:", ds.lat.values[0], "to", ds.lat.values[-1])
print("Lon:", ds.lon.values[0], "to", ds.lon.values[-1])

# Check mhw per day
mhw_per_day = ds.mhw.values.sum(axis=(1,2))
print("\nMHW cells per day:")
for t in range(len(ds.time)):
    print(f"  {ds.time.values[t]}: {mhw_per_day[t]}")

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))

# Verify output directory
import os
print("\nFiles in output:")
for f in os.listdir('output'):
    print(f"  {f}: {os.path.getsize(os.path.join('output', f))} bytes")
