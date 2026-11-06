
import fsspec, xarray as xr, numpy as np, datetime as dt, time, os
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
need=[]
d=dt.date(1991,12,27)
while d<=dt.date(2003,1,5):
    need.append(d); d+=dt.timedelta(1)
d=dt.date(2013,6,1)
while d<=dt.date(2013,8,31):
    need.append(d); d+=dt.timedelta(1)
LA=slice(None); 
def load(d):
    p=f"{base}/sst_{d:%Y%m%d}.nc"
    with fs.open(p,'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf')
        ds.load()
    lat=ds.latitude.values; lon=ds.longitude.values
    la=np.where((lat>=64.39)&(lat<=65.59))[0]; lo=np.where((lon>=23.41)&(lon<=24.61))[0]
    v=ds.analysed_sst.values[0][np.ix_(la,lo)].astype(np.float64)
    t=ds.time.values[0]
    ok = (np.datetime64(d,'D')==t.astype('datetime64[D]'))
    return d, v, lat[la], lon[lo], ok
t0=time.time()
res={}
with ThreadPoolExecutor(16) as ex:
    for d,v,la_,lo_,ok in ex.map(load, need):
        res[d]=(v,la_,lo_,ok)
print(time.time()-t0, len(res))
print('time mismatches', sum(not r[3] for r in res.values()))
lat0=res[need[0]][1]; lon0=res[need[0]][2]
print(all(np.array_equal(r[1],lat0) and np.array_equal(r[2],lon0) for r in res.values()))
S=np.stack([res[d][0] for d in need])  # (ndays,60,60)
np.savez('/tmp/sub.npz', S=S, lat=lat0, lon=lon0, dates=np.array([str(d) for d in need]))
print(S.shape, np.isnan(S).sum())
