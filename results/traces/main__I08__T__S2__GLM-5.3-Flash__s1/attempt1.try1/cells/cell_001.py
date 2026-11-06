import traceback
try:
    import fsspec, xarray as xr, numpy as np, pandas as pd, collections
    fs = fsspec.filesystem('onedata')
    path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
    f = fs.open(path, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print('GLOBAL:', {k: str(v)[:80] for k, v in list(ds.attrs.items())[:8]})
    t = pd.DatetimeIndex(ds['time'].values)
    print('TIME:', t[0], '->', t[-1], 'n=', t.size, 'monotonic=', t.is_monotonic_increasing)
    dtd = np.diff(t.values).astype('timedelta64[D]').astype(int)
    print('steps(days):', collections.Counter(dtd.tolist()).most_common(3))
    v0 = [vn for vn in ds.data_vars if ds[vn].ndim == 3][0]
    td, yd, xd = ds[v0].dims
    print('DIMS of', v0, ':', ds[v0].dims)
    la = np.asarray(ds[yd].values, float); lo = np.asarray(ds[xd].values, float)
    print('lat n=', la.size, 'min', la.min(), 'max', la.max(), 'step', np.unique(np.round(np.diff(la),6))[:5])
    print('lon n=', lo.size, 'min', lo.min(), 'max', lo.max(), 'step', np.unique(np.round(np.diff(lo),6))[:5])
    print('lat in [54.75,54.87]:', la[(la>54.75)&(la<54.87)])
    print('lat in [55.95,56.07]:', la[(la>55.95)&(la<56.07)])
    print('lon in [19.55,19.67]:', lo[(lo>19.55)&(lo<19.67)])
    print('lon in [20.75,20.87]:', lo[(lo>20.75)&(lo<20.87)])
    for vn in list(ds.data_vars):
        v = ds[vn]
        print('VAR', vn, v.dims, v.dtype, {k: str(w)[:60] for k, w in v.attrs.items()})
    f.close()
except Exception:
    traceback.print_exc()
