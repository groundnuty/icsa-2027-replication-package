
import xarray as xr
import numpy as np

# Read back the output files
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print()
print(f'mhw data type: {ds['mhw'].dtype}')
print(f'mhw shape: {ds['mhw'].shape}')
print(f'mhw values: unique = {np.unique(ds['mhw'].values)}')
print(f'mhw sum: {ds['mhw'].values.sum()}')

import json
with open('output/report.json') as f:
    report = json.load(f)
print(f'\nReport: {json.dumps(report, indent=2)}')
