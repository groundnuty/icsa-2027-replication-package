
import fsspec, xarray as xr, numpy as np, datetime as dt, time, os
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
d0=dt.date(1991,12,27); d1=dt.date(2003,1,5)
dates=[]
d=d0
while d<=d1:
    dates.append(d); d+=dt.timedelta(1)
t=dt.date(2019,6,1)
while t<=dt.date(2019,8,31):
    dates.append(t); t+=dt.timedelta(1)
def load(d):
    with fs.open(base+f'sst_{d:%Y%m%d}.nc','rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf').load()
    ds=ds.sel(latitude=slice(56.0,57.5),longitude=slice(17.6,19.0))
    return ds
t0=time.time()
x=load(dates[0]); print(time.time()-t0, x.latitude.values[[0,-1]], x.longitude.values[[0,-1]], x.latitude.size, x.longitude.size)
