
import numpy as np
import xarray as xr
import json

# Verify the NetCDF file
ds_check = xr.open_dataset('output/mhw_mask.nc')
print(ds_check)
print('mhw dtype:', ds_check.mhw.dtype)
print('mhw shape:', ds_check.mhw.shape)
print('mhw values:', np.unique(ds_check.mhw.values))
print('time:', ds_check.time.values[0], ds_check.time.values[-1])
print('lat:', ds_check.lat.values[0], ds_check.lat.values[-1])
print('lon:', ds_check.lon.values[0], ds_check.lon.values[-1])
ds_check.close()

# Verify report
with open('output/report.json') as f:
    report = json.load(f)
print('\nReport:', json.dumps(report, indent=2))
