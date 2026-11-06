
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(ds)
print()
print("mhw dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)
print("mhw values unique:", np.unique(ds['mhw'].values))
print("mhw sum:", ds['mhw'].values.sum())
print("mhw time range:", ds['time'].values[0], "to", ds['time'].values[-1])
print()

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("report.json:")
print(json.dumps(report, indent=2))
