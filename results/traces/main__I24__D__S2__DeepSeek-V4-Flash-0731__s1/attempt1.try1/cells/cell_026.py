
import xarray as xr
import numpy as np
import json

# Read back the output files
mhw_ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("MHW mask dataset:")
print(mhw_ds)
print()
print("mhw dtype:", mhw_ds.mhw.dtype)
print("mhw shape:", mhw_ds.mhw.shape)
print("time range:", mhw_ds.time.values[0], "to", mhw_ds.time.values[-1])
print("lat range:", mhw_ds.lat.values[0], "to", mhw_ds.lat.values[-1])
print("lon range:", mhw_ds.lon.values[0], "to", mhw_ds.lon.values[-1])
print("mhw sum:", mhw_ds.mhw.values.sum())
print("mhw unique values:", np.unique(mhw_ds.mhw.values))

# Check report
with open('output/report.json') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))
