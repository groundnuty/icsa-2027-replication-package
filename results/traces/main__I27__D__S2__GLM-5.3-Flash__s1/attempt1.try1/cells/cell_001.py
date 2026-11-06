import fsspec, os, time
fs = fsspec.filesystem('onedata')
remote = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local = '/work/sst_s2.nc'
t0=time.time()
if not os.path.exists(local):
    fs.get(remote, local)
print('size MB:', os.path.getsize(local)/1e6, 'dl s:', round(time.time()-t0,1))

import xarray as xr, numpy as np
ds = xr.open_dataset(local, engine='h5netcdf')
print('dims:', dict(ds.sizes))
for v in ds.variables:
    a = ds[v]
    u = a.attrs.get('units','')
    print(v, a.dims, a.dtype, u, {k:a.attrs[k] for k in list(a.attrs)[:3] if k!='units'})
print('time0', str(ds.time.values[0]), 'timeN', str(ds.time.values[-1]), 'n', ds.sizes['time'])
print('lat', float(ds.lat.min()), float(ds.lat.max()), 'n', ds.sizes['lat'])
print('lon', float(ds.lon.min()), float(ds.lon.max()), 'n', ds.sizes['lon'])
