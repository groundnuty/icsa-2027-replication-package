
import xarray as xr
import numpy as np

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print('mhw dtype:', ds['mhw'].dtype)
print('mhw shape:', ds['mhw'].shape)
print('mhw encoding:', ds['mhw'].encoding)

# Also check the report file
import json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print('\nReport keys:', list(report.keys()))
print('Report complete:', report['complete'])
print('Report caveats:', report['caveats'])
print('Report events:', report['events'])
