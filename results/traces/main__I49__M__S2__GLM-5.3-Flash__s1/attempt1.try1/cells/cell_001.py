import os
import numpy as np, xarray as xr
print('cwd', os.getcwd())
print('numpy', np.__version__, 'xarray', xr.__version__)
for m in ('netCDF4','h5netcdf','h5py','cftime','pandas'):
    try:
        mod = __import__(m); print(m, getattr(mod,'__version__','?'))
    except Exception as e:
        print(m, 'MISSING', repr(e)[:80])
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
print('exists', os.path.exists(p), 'size', os.path.getsize(p) if os.path.exists(p) else None)
try:
    open('/tmp/_persist_test','w').write('x'); print('/tmp writable')
except Exception as e: print('/tmp NOT writable', e)
try:
    open('_persist_test2','w').write('x'); print('cwd writable')
except Exception as e: print('cwd NOT writable', e)
ds = xr.open_dataset(p, engine='h5netcdf')
print(ds)
t = ds['time'].values
print('time dtype', t.dtype, 'n=', t.size)
print('t0', t[0], 't-1', t[-1])
d = t.astype('datetime64[D]')
step = np.unique(np.diff(d))
print('unique day steps (first 10):', step[:10])
lat = ds['lat'].values; lon = ds['lon'].values
print('lat dims', ds['lat'].dims, 'dtype', lat.dtype, 'n', lat.size, 'min/max', lat.min(), lat.max())
print('lon dims', ds['lon'].dims, 'dtype', lon.dtype, 'n', lon.size, 'min/max', lon.min(), lon.max())
print('lat uniq steps', np.unique(np.round(np.diff(lat),6))[:8])
print('lon uniq steps', np.unique(np.round(np.diff(lon),6))[:8])
for v in ds.data_vars:
    a = ds[v]
    print('VAR', v, a.dtype, dict(a.attrs))
print('time attrs', ds['time'].attrs)
print('var encodings _FillValue:', {v: ds[v].encoding.get('_FillValue', None) for v in ds.data_vars})
print('chunksizes', ds.encoding.get('chunksizes', None))
