import os, traceback
import fsspec
fs = fsspec.filesystem('onedata')
os.makedirs('/work', exist_ok=True)
cands = ['icsa2027_data_20261101T090944Z/s2z/sst_s2.nc',
         '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc']
ok = False
for c in cands:
    try:
        fs.get(c, '/work/sst_s2.nc')
        print('downloaded via:', c, 'size:', os.path.getsize('/work/sst_s2.nc'))
        ok = True
        break
    except Exception as e:
        print('failed:', c, repr(e)[:300])
if ok:
    import xarray as xr, numpy as np
    print('numpy', np.__version__)
    ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
    print('dims:', dict(ds.sizes))
    print('vars:', list(ds.data_vars))
    for v in ds.data_vars:
        print(v, ds[v].dtype, ds[v].dims, dict(ds[v].sizes))
    for c in ds.coords:
        print('coord', c, ds[c].dtype, ds[c].dims)
    t = ds['time'].values
    print('time[0]', t[0], 'time[-1]', t[-1], 'n=', len(t))
    for cn in ('lat','latitude'):
        if cn in ds.coords or cn in ds.variables:
            la = ds[cn].values
            print(cn, la.dtype, 'min', np.nanmin(la), 'max', np.nanmax(la), 'shape', la.shape, '1D' if la.ndim==1 else '2D')
            print(' first5', la.ravel()[:5])
    for cn in ('lon','longitude'):
        if cn in ds.coords or cn in ds.variables:
            lo = ds[cn].values
            print(cn, lo.dtype, 'min', np.nanmin(lo), 'max', np.nanmax(lo), 'shape', lo.shape)
            print(' first5', lo.ravel()[:5])
