
import fsspec, xarray as xr, re, numpy as np, os, json, pickle, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z'
def d2s(d): return d.strftime('%Y%m%d')
need=[]
d=dt.date(1991,12,27)
while d<=dt.date(2003,1,5): need.append(d); d+=dt.timedelta(1)
d=dt.date(2010,6,1)
while d<=dt.date(2010,8,31): need.append(d); d+=dt.timedelta(1)
def load(d):
    with fs.open(f'{P}/sst_{d2s(d)}.nc','rb') as f:
        x=xr.open_dataset(f, engine='h5netcdf').load()
    x=x.sel(latitude=slice(60.4,61.8), longitude=slice(17.2,18.5))
    return d, x.analysed_sst.values.astype(np.float64)[0], x.latitude.values, x.longitude.values
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(load, need))
lat=res[0][2]; lon=res[0][3]
print(lat, lon)
dates=[r[0] for r in res]; arr=np.stack([r[1] for r in res])
print(arr.shape, np.isnan(arr).mean())
pickle.dump((dates,arr,lat,lon), open('/tmp/sst.pkl','wb'))
