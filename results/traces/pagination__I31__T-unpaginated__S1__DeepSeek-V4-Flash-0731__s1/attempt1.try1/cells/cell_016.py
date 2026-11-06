
import numpy as np
import json

# Read back the output files to verify
import xarray as xr

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print("mhw shape:", ds.mhw.shape)
print("mhw unique values:", np.unique(ds.mhw.values))
print("mhw sum:", ds.mhw.values.sum())
print("time:", ds.time.values[:5])
print("time:", ds.time.values[-5:])

# Check the report
with open('output/report.json') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))
