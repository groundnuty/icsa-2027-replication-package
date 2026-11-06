
import json,xarray as xr
print(open('/tmp/../'+'output/report.json').read() if False else '')
import os
print(os.path.exists('output/mhw_mask.nc'), os.path.exists('output/report.json'))
print(json.load(open('output/report.json'))['events'])
m=xr.open_dataset('output/mhw_mask.nc'); print(m.mhw.dims, m.mhw.shape, m.mhw.dtype)
