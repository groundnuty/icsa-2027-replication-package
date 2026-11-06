import fsspec, xarray as xr, numpy as np, time, os, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
B='icsa2027_data_20261101T090944Z/s1z/'
def load(day):
    p=B+f"sst_{day.strftime('%Y%m%d')}.nc"
    with fs.open(p,'rb') as f:
        d=xr.open_dataset(f,engine='h5netcdf')
        la=d.latitude.values; lo=d.longitude.values
        ilat=np.where((la>=57.83-1e-6)&(la<=59.03+1e-6))[0]; ilon=np.where((lo>=17.41-1e-6)&(lo<=18.61+1e-6))[0]
        v=d.analysed_sst.isel(latitude=ilat,longitude=ilon).values.astype(np.float64)
        d.close()
    return v, la[ilat], lo[ilon]
days=[dt.date(1991,12,27)+dt.timedelta(i) for i in range((dt.date(2003,1,5)-dt.date(1991,12,27)).days+1)]
tdays=[dt.date(2008,6,1)+dt.timedelta(i) for i in range(92)]
alld=days+tdays
t0=time.time()
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(load, alld))
print(time.time()-t0, len(res))
V=np.stack([r[0][0] for r in res]); LA=res[0][1]; LO=res[0][2]
np.savez('/tmp/cache.npz', V=V, LA=LA, LO=LO, dates=np.array([d.strftime('%Y%m%d') for d in alld]))
print(V.shape, np.isnan(V).sum())