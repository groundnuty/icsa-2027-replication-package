
import fsspec, xarray as xr, io, numpy as np, pandas as pd, json, os, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
dates = pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2021-06-01','2021-08-31'))
dates = pd.DatetimeIndex(sorted(set(dates)))
def load(d):
    p=f"{base}/sst_{d:%Y%m%d}.nc"
    with fs.open(p,'rb') as f:
        ds=xr.open_dataset(io.BytesIO(f.read()),engine='h5netcdf'); ds.load()
    lat=ds.latitude.values; lon=ds.longitude.values
    m=(lat>=54.39)&(lat<=55.59); n=(lon>=18.25)&(lon<=19.45)
    arr=ds.analysed_sst.values[0][np.ix_(m,n)].astype(np.float64)
    out=(pd.Timestamp(ds.time.values[0]).normalize(),arr,lat[m].astype(np.float64),lon[n].astype(np.float64),ds.analysed_sst.attrs.get('units'))
    ds.close(); return out
t0=time.time()
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(load, dates))
print('loaded',time.time()-t0)
times=[r[0] for r in res]
assert all(t==d for t,d in zip(times,dates))
LAT=res[0][2]; LON=res[0][3]
assert all(np.array_equal(r[2],LAT) and np.array_equal(r[3],LON) for r in res)
print(set(r[4] for r in res), LAT.shape, LON.shape, LAT[[0,-1]], LON[[0,-1]])
X=np.stack([r[1] for r in res])
np.savez('/tmp/cache.npz',X=X,dates=dates.values,LAT=LAT,LON=LON)
bl_mask=(dates<=pd.Timestamp('2003-01-05'))&(dates>=pd.Timestamp('1991-12-27'))
tg_mask=(dates>=pd.Timestamp('2021-06-01'))&(dates<=pd.Timestamp('2021-08-31'))
Xt=X[tg_mask]; tdates=dates[tg_mask]
sea=np.all(np.isfinite(Xt),axis=0)
print('sea cells', sea.sum(), 'of', sea.size, 'target days', len(tdates))
print('partial NaN cells in target', (np.isfinite(Xt).any(0) & ~sea).sum())
print('baseline NaN frac among sea cells', np.isnan(X[bl_mask][:,sea]).mean())
print('target range', np.nanmin(Xt), np.nanmax(Xt), 'all range', np.nanmin(X), np.nanmax(X))
