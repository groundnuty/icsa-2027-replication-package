import fsspec, xarray as xr, io, numpy as np, pandas as pd, time, pickle
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
dates = pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2021-06-01','2021-08-31'))
dates = pd.DatetimeIndex(sorted(set(dates)))
latsel=None
def load(d):
    p=f"{base}/sst_{d:%Y%m%d}.nc"
    try:
        with fs.open(p,'rb') as f:
            ds=xr.open_dataset(io.BytesIO(f.read()),engine='h5netcdf')
            ds.load()
        lat=ds.latitude.values; lon=ds.longitude.values
        m=(lat>=54.39)&(lat<=55.59); n=(lon>=18.25)&(lon<=19.45)
        arr=ds.analysed_sst.values[0][np.ix_(m,n)].astype(np.float64)
        t=pd.Timestamp(ds.time.values[0]).normalize()
        out=(t,arr,lat[m],lon[n],ds.analysed_sst.attrs.get('units'))
        ds.close(); return out
    except Exception as e:
        return ('ERR',d,repr(e)[:300])
t0=time.time()
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(load, dates))
print(time.time()-t0, len(res))
errs=[r for r in res if r[0]=='ERR']
print(len(errs), errs[:3])
