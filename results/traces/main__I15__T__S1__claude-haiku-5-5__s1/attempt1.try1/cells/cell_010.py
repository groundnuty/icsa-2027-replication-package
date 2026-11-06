
import fsspec, xarray as xr, numpy as np, datetime as dt, time, os, json
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
    return ds['analysed_sst'].values[0].astype(np.float64), ds.latitude.values.astype(float), ds.longitude.values.astype(float)
t0=time.time()
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(load,dates))
print('loaded',time.time()-t0)
lat=res[0][1]; lon=res[0][2]
la=np.where((lat>=56.13-1e-6)&(lat<=57.33+1e-6))[0]
lo=np.where((lon>=17.71-1e-6)&(lon<=18.91+1e-6))[0]
arr=np.stack([r[0][np.ix_(la,lo)] for r in res])
rlat=lat[la]; rlon=lon[lo]
print('region', arr.shape, rlat[0],rlat[-1],rlon[0],rlon[-1])
os.makedirs('/tmp',exist_ok=True)
np.savez('/tmp/sst_region.npz', sst=arr, dates=np.array([str(x) for x in dates]), lat=rlat, lon=rlon)

# day-of-year mapping
def doy(x):
    leap = lambda y: (y%4==0 and y%100!=0) or y%400==0
    # leap-year mapping: Feb29=60, Mar1=61 in leap; non-leap Mar1=61 too (no day 60)
    # use Feb29 ->60 ; for non-leap Feb28=59, Mar1=61
    cum=[0,31,59,90,120,151,181,212,243,273,304,334]  # days before month in non-leap
    # map as in spec: Feb29=60, Mar1=61 ; non-leap: Mar1=61 too
    m,dd=x.month,x.day
    if m==2 and dd==29: return 60
    c=[0,31,59,91,121,152,182,213,244,274,305,335]  # days before month, with 60 skipped
    # for months >=3 : doy = (non-leap doy)+1 if ...
    nl=[0,31,59,90,120,151,181,212,243,273,304,334][m-1]+dd
    if m>=3: return nl+1 if False else nl+ (1 if False else 0) if False else (nl+1 if m>=3 else nl)
    return nl
# simpler explicit: non-leap doy for Mar+ is cum+dd where Feb28=59 and Mar1=61 -> nl+1 for months>=3
def doy2(x):
    if x.month==2 and x.day==29: return 60
    nl=[0,31,59,90,120,151,181,212,243,273,304,334][x.month-1]+x.day
    return nl+1 if x.month>=3 else nl
print(doy2(dt.date(2019,6,1)), doy2(dt.date(2019,12,31)), doy2(dt.date(1992,12,31)), doy2(dt.date(1992,2,29)), doy2(dt.date(1992,3,1)), doy2(dt.date(1993,3,1)))
