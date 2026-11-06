import os, fsspec, numpy as np
print('cwd:', os.getcwd())
fs = fsspec.filesystem('onedata')
remote = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
try:
    print('ls parent:', fs.ls('icsa2027_data_20261101T090944Z/s2z'))
except Exception as e:
    print('ls error:', repr(e))
os.makedirs('/work', exist_ok=True)
local = '/work/sst_s2.nc'
fs.get(remote, local)
print('downloaded size:', os.path.getsize(local))

import xarray as xr
try:
    ds = xr.open_dataset(local, engine='h5netcdf')
except Exception as e:
    print('h5netcdf failed:', repr(e))
    ds = xr.open_dataset(local)
print(ds)
