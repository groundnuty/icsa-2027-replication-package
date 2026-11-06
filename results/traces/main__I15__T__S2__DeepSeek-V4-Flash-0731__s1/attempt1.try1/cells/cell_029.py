
import numpy as np
import json

# Verify report
with open('output/report.json') as f:
    report = json.load(f)
print('Report keys:', list(report.keys()))
print(json.dumps(report, indent=2))

# Verify mask
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc')
print('\nmhw_mask.nc:')
print('  Dimensions:', dict(ds.sizes))
print('  mhw dtype:', ds.mhw.dtype)
print('  mhw unique values:', np.unique(ds.mhw.values))
print('  time range:', ds.time.values[0], 'to', ds.time.values[-1])
print('  lat range:', ds.lat.values[0], 'to', ds.lat.values[-1])
print('  lon range:', ds.lon.values[0], 'to', ds.lon.values[-1])
ds.close()
