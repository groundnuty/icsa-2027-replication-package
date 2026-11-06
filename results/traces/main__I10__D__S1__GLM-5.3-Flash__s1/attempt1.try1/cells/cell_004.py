import fsspec, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

for d in ['19911227','19920101','19920229','20001231','20021231','20030105','20050601','20050831','20050602']:
    p = f'{base}/sst_{d}.nc'
    try:
        ex = fs.exists(p)
        inf = fs.info(p) if ex else None
        print(d, ex, inf.get('size') if inf else None)
    except Exception as e:
        print(d, 'ERR', repr(e))

# download one file and inspect
os_ok = True
import os
os.makedirs('/work/tmp', exist_ok=True)
t0=time.time()
fs.get(f'{base}/sst_19920715.nc', '/work/tmp/sample.nc')
print('download s:', round(time.time()-t0,2), 'size:', os.path.getsize('/work/tmp/sample.nc'))

import xarray as xr
ds = xr.open_dataset('/work/tmp/sample.nc', engine='h5netcdf')
print(ds)
print('---')
print('lat range:', float(ds.lat.min()), float(ds.lat.max()), 'n:', ds.lat.size)
print('lon range:', float(ds.lon.min()), float(ds.lon.max()), 'n:', ds.lon.size)
print('time:', ds.time.values[:3], ds.time.values[-1] if ds.time.size>1 else '')
for v in ds.data_vars:
    print(v, ds[v].dtype, ds[v].attrs)
print('lat attrs:', ds.lat.attrs)
print('lon attrs:', ds.lon.attrs)
print('time attrs:', ds.time.attrs)
