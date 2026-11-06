import fsspec, numpy as np, xarray as xr
print('numpy', np.__version__, '| xarray', xr.__version__)
fs = fsspec.filesystem('onedata')
P = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
found = None
for c in [P, '/'+P, '~/'+P, '~/'+P]:
    try:
        info = fs.info(c)
        print('FOUND:', c, 'size=', info.get('size'))
        found = c
        break
    except Exception as e:
        print('miss:', c, type(e).__name__, str(e)[:120])
if found is None:
    for d in ['', '/', '~', '~']:
        try:
            print(repr(d), '->', fs.ls(d)[:20])
        except Exception as e:
            print(repr(d), 'ERR', str(e)[:120])
else:
    f = fs.open(found, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    print('sizes', dict(ds.sizes))
    print('data_vars', list(ds.data_vars))
    for v in ds.data_vars:
        print(v, ds[v].dtype, ds[v].dims, 'units=', ds[v].attrs.get('units'), '| long_name=', str(ds[v].attrs.get('long_name'))[:60])
    print('global title:', str(ds.attrs.get('title'))[:100])
    t = ds.time.values
    print('time dtype', t.dtype, 'first', t[0], 'last', t[-1], 'n', len(t))
    latv=ds.lat.values; lonv=ds.lon.values
    print('lat', float(latv.min()), float(latv.max()), len(latv))
    print('lon', float(lonv.min()), float(lonv.max()), len(lonv))
    print('lat spacing sample', np.diff(latv[100:103]))
    print('lon spacing sample', np.diff(lonv[100:103]))
    mlat=(latv>=60.09)&(latv<=61.29); mlon=(lonv>=20.01)&(lonv<=21.21)
    print('region cells', int(mlat.sum()), 'x', int(mlon.sum()), '=', int(mlat.sum()*mlon.sum()))
    print('lat in region', latv[mlat])
    print('lon in region', lonv[mlon])
    v0=list(ds.data_vars)[0]
    sub=ds[v0].isel(time=0, lat=mlat, lon=mlon).values
    print('sample t0 vals', sub.ravel()[:5], 'min/max', float(np.nanmin(sub)), float(np.nanmax(sub)))
    sel = ds[v0].sel(time=slice('2003-06-01','2003-08-31'))
    print('target days', sel.sizes['time'])
    s1 = ds[v0].sel(time=slice('1991-12-27','1992-01-06'))
    print('early boundary days', s1.sizes['time'], s1.time.values[:3], s1.time.values[-2:])
    s2 = ds[v0].sel(time=slice('2002-12-26','2003-01-06'))
    print('late boundary days', s2.sizes['time'], s2.time.values[:2], s2.time.values[-2:])
    print('hazen test (expect ~9.9667):', float(np.quantile(np.arange(1,11,dtype=float), 0.9, method='hazen')))
    ds.close(); f.close()
    print('PATH_OK', found)
