
import fsspec, xarray as xr, numpy as np, datetime as dt, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
d0=dt.date(1991,12,27); d1=dt.date(2003,1,5)
dates=[]; d=d0
while d<=d1: dates.append(d); d+=dt.timedelta(1)
t=dt.date(2019,6,1)
while t<=dt.date(2019,8,31): dates.append(t); t+=dt.timedelta(1)
def load(d):
    with fs.open(base+f'sst_{d:%Y%m%d}.nc','rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf').load()
    ds=ds.sel(latitude=slice(56.0,57.5),longitude=slice(17.6,19.0))
    return ds
t0=time.time()
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(load,dates))
print('loaded',time.time()-t0, len(res))
lat=res[0].latitude.values.astype(float); lon=res[0].longitude.values.astype(float)
print(lat[:3],lat[-3:],lon[:3],lon[-3:])
print(np.unique(np.round(np.diff(lat),5)), np.unique(np.round(np.diff(lon),5)))
ntimes=set(r.sizes['time'] for r in res); print(ntimes)
